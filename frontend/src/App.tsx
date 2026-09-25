import { BrowserRouter, Routes, Route } from 'react-router-dom'
import AppShell from '@/components/AppShell'
import ConsultationView from './ConsultationView'
import Home from '@/pages/Home'
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import Booking from '@/pages/Booking'
import BillingDashboard from '@/pages/BillingDashboard'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Home />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/booking" element={<Booking />} />
          <Route path="/billing" element={<BillingDashboard />} />
          <Route path="/consultation/:appointmentId" element={<ConsultationView />} />
          <Route path="*" element={
            <div className="flex flex-col items-center justify-center min-h-[50vh] text-center">
              <h2 className="text-2xl font-semibold text-slate-800 mb-2">404 - Page Not Found</h2>
              <p className="text-slate-500">The page you are looking for does not exist.</p>
            </div>
          } />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
