"""
model_loader.py
---------------
Loads and manages the intent classification model.

The model is a fine-tuned BertForSequenceClassification (AlephBERT base)
trained to classify Hebrew utterances into 10 voice-command intent classes:

    0: call         — "תתקשרי לאמא"
    1: alarm        — "תעירי אותי בשש בבוקר"
    2: sms          — "תשלחי הודעה לדוד"
    3: search_query — "תחפשי לי מידע על..."
    4: navigation   — "תנווטי אותי לתל אביב"
    5: calendar     — "תוסיפי פגישה ביומן"
    6: camera       — "תצלמי תמונה"
    7: weather      — "מה מזג האוויר"
    8: notes        — "תכתבי לי פתק"
    9: flashlight   — "תדליקי פנס"

Design rationale
----------------
Loading is intentionally deferred (NOT done at import time). The model is
loaded once via the `load()` method, which is called from FastAPI's lifespan
context manager at server startup. This ensures:
  - The server process starts quickly and can be health-checked before heavy
    weights (768-dim BERT) are in memory.
  - The weights are shared across all requests within the same process, so
    there is zero per-request cold-start overhead after startup.
  - Tests can control exactly when loading happens via fixtures.
"""

import logging
from pathlib import Path
from typing import Dict, Tuple, Union

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

logger = logging.getLogger(__name__)


class IntentClassifier:
    """
    Wraps the fine-tuned AlephBERT intent classification model.

    Usage
    -----
        classifier = IntentClassifier(model_dir="intent_model")
        classifier.load()                        # called once at startup
        intent_id, label = classifier.predict("תתקשרי לאמא שלי")
        # → (0, "call")
    """

    def __init__(self, model_dir: Union[str, Path]) -> None:
        """
        Initialize the classifier with the path to the model directory.

        Args:
            model_dir: Path to the directory containing model weights
                       (model.safetensors), tokenizer files, and config.json.
                       Can be absolute or relative to the current working directory.
        """
        self.model_dir = Path(model_dir)
        self.tokenizer = None
        self.model = None
        # Maps integer class index → human-readable label, e.g. {2: "sms"}
        self.id2label: Dict[int, str] = {}
        self._loaded = False

    def load(self) -> None:
        """
        Load the tokenizer and model weights from disk into memory.

        This method is called once at application startup. It is blocking and
        will take several seconds on the first run (or if weights are not
        cached). Subsequent calls are no-ops (guarded by self._loaded).

        After this call, self.tokenizer, self.model, and self.id2label are
        all populated and ready for inference.

        Raises:
            FileNotFoundError: If model_dir does not exist on disk.
            OSError: If the model weights cannot be read (e.g. corrupted file).
        """
        if self._loaded:
            logger.debug("Intent classifier already loaded — skipping.")
            return

        if not self.model_dir.exists():
            raise FileNotFoundError(
                f"Intent model directory not found: {self.model_dir.resolve()}\n"
                "Make sure intent_model/ is present in the repository root."
            )

        logger.info("Loading intent classifier tokenizer from: %s", self.model_dir.resolve())
        self.tokenizer = AutoTokenizer.from_pretrained(str(self.model_dir))

        logger.info("Loading intent classifier model weights from: %s", self.model_dir.resolve())
        self.model = AutoModelForSequenceClassification.from_pretrained(str(self.model_dir))

        # Switch to eval mode: disables dropout layers that are only needed
        # during training. This is required for deterministic inference.
        self.model.eval()

        # Read the id→label mapping from the model's own config so we never
        # hard-code label strings in application code.
        self.id2label = {
            int(k): v
            for k, v in self.model.config.id2label.items()
        }

        self._loaded = True
        logger.info(
            "Intent classifier ready — %d classes: %s",
            len(self.id2label),
            list(self.id2label.values()),
        )

    def predict(self, utterance: str) -> Tuple[int, str]:
        """
        Classify a Hebrew utterance into one of the 10 intent classes.

        The utterance is tokenized, passed through the BERT model, and the
        class with the highest logit score is returned.

        Args:
            utterance: Raw Hebrew text from the user. May be of any length;
                       tokens beyond 512 are truncated (BERT's hard limit).

        Returns:
            A tuple (intent_id, intent_label), e.g. (2, "sms").

        Raises:
            RuntimeError: If load() has not been called before predict().
        """
        if not self._loaded:
            raise RuntimeError(
                "Intent classifier has not been loaded. Call load() first."
            )

        # Tokenize with truncation to BERT's 512-token maximum.
        # return_tensors="pt" gives PyTorch tensors ready for the model.
        inputs = self.tokenizer(
            utterance,
            return_tensors="pt",
            truncation=True,
            max_length=512,
        )

        # Disable gradient computation — we only need the forward pass for
        # inference, not backprop. This saves memory and speeds up the call.
        with torch.no_grad():
            outputs = self.model(**inputs)

        # outputs.logits shape: [batch_size=1, num_classes=10]
        # argmax over the class dimension gives the predicted class index.
        intent_id = int(torch.argmax(outputs.logits, dim=-1).item())
        intent_label = self.id2label.get(intent_id, "unknown")

        logger.debug("predict(%r) → %d (%s)", utterance[:40], intent_id, intent_label)
        return intent_id, intent_label
