import { BrowserRouter, Routes, Route } from 'react-router-dom'
import ConsultationView from './ConsultationView'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/consultation/:appointmentId" element={<ConsultationView />} />
        <Route path="*" element={
          <div style={{
            minHeight: '100vh', display: 'flex', flexDirection: 'column',
            alignItems: 'center', justifyContent: 'center',
            background: '#0f1117', color: '#94a3b8', fontFamily: 'system-ui',
          }}>
            <h1 style={{ color: '#e2e8f0', marginBottom: '0.5rem' }}>🏥 Clinic Booking System</h1>
            <p>Navigate to <code>/consultation/:appointmentId</code> to open the doctor console.</p>
          </div>
        } />
      </Routes>
    </BrowserRouter>
  )
}

export default App
