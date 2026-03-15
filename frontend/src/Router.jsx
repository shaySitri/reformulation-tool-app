/**
 * Router.jsx
 * ----------
 * Top-level routing wrapper for the application.
 *
 * Routes:
 *   /       → main user-facing interface (App)
 *   /stats  → developer / operator statistics page (StatsPage)
 *
 * The /stats route is intentionally not linked from the main UI.
 * It is accessible by URL only, intended for developer inspection.
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App.jsx'
import StatsPage from './pages/StatsPage.jsx'

function Router() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/stats" element={<StatsPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default Router
