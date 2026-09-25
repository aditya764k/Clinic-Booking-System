import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh]">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 sm:text-5xl mb-4">
          Clinic Appointment Manager
        </h1>
        <p className="text-xl text-slate-600 max-w-2xl mx-auto">
          Manage your patients, streamline appointments, and seamlessly integrate AI-assisted clinical notes into your workflow.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-5xl">
        <Card>
          <CardHeader>
            <CardTitle>Patients</CardTitle>
            <CardDescription>Book and manage appointments</CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/booking">
              <Button className="w-full">Book Appointment</Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Receptionists</CardTitle>
            <CardDescription>Manage daily check-ins and billing</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <Link to="/login">
              <Button variant="secondary" className="w-full">Login</Button>
            </Link>
            <Link to="/billing">
              <Button variant="outline" className="w-full border-teal-200 text-teal-700 hover:bg-teal-50">
                Billing Desk
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Doctors</CardTitle>
            <CardDescription>View queues and write clinical notes</CardDescription>
          </CardHeader>
          <CardContent>
            <Link to="/login">
              <Button variant="outline" className="w-full">Doctor Login</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
