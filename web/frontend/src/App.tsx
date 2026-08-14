import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { HomePage } from './pages/HomePage'
import { MethodologyPage } from './pages/MethodologyPage'
import { PredictPage } from './pages/PredictPage'
import { EvaluatePage } from './pages/EvaluatePage'
import { ResultsPage } from './pages/ResultsPage'
import { Wc2026Page } from './pages/Wc2026Page'
import { FeaturesPage } from './pages/FeaturesPage'
import { LimitationsPage } from './pages/LimitationsPage'
import { AboutPage } from './pages/AboutPage'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="methodology" element={<MethodologyPage />} />
          <Route path="predict" element={<PredictPage />} />
          <Route path="evaluate" element={<EvaluatePage />} />
          <Route path="results" element={<ResultsPage />} />
          <Route path="wc2026" element={<Wc2026Page />} />
          <Route path="features" element={<FeaturesPage />} />
          <Route path="limitations" element={<LimitationsPage />} />
          <Route path="about" element={<AboutPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
