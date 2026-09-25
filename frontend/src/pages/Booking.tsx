import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const MOCK_DOCTORS = [
  { id: 1, name: 'Dr. Sarah Smith', specialty: 'General Practice' },
  { id: 2, name: 'Dr. James Wilson', specialty: 'Cardiology' },
]

const MOCK_SLOTS = [
  { id: 101, time: '09:00 AM', status: 'available' },
  { id: 102, time: '09:30 AM', status: 'booked' },
  { id: 103, time: '10:00 AM', status: 'available' },
  { id: 104, time: '10:30 AM', status: 'available' },
]

export default function Booking() {
  const [selectedDoctor, setSelectedDoctor] = useState<number | null>(null)
  const [bookingStatus, setBookingStatus] = useState<string | null>(null)

  const handleBook = (slotId: number) => {
    setBookingStatus(`Successfully booked slot #${slotId}! (Mock)`)
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      <div className="text-center">
        <h2 className="text-3xl font-bold text-slate-900">Book an Appointment</h2>
        <p className="text-slate-500 mt-2">Select a doctor to view their available slots today.</p>
      </div>

      {bookingStatus && (
        <div className="p-4 bg-primary/10 text-primary border border-primary/20 rounded-md font-medium text-center">
          {bookingStatus}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {MOCK_DOCTORS.map((doc) => (
          <Card 
            key={doc.id} 
            className={`cursor-pointer transition-all ${
              selectedDoctor === doc.id ? 'ring-2 ring-primary border-primary shadow-md' : 'hover:border-primary/50'
            }`}
            onClick={() => {
              setSelectedDoctor(doc.id)
              setBookingStatus(null)
            }}
          >
            <CardHeader>
              <CardTitle>{doc.name}</CardTitle>
              <CardDescription>{doc.specialty}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>

      {selectedDoctor && (
        <Card className="mt-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
          <CardHeader>
            <CardTitle>Available Slots Today</CardTitle>
            <CardDescription>Select a time to confirm your appointment.</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {MOCK_SLOTS.map((slot) => (
                <Button
                  key={slot.id}
                  variant={slot.status === 'available' ? 'outline' : 'secondary'}
                  disabled={slot.status !== 'available'}
                  onClick={() => handleBook(slot.id)}
                  className="w-full"
                >
                  {slot.time}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
