import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

export default function Register() {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoading(true)
    setError(null)

    if (!name || !email || !password) {
      setError('Please fill in all fields.')
      setIsLoading(false)
      return
    }

    // Mock API call
    setTimeout(() => {
      setIsLoading(false)
      setError('Registration is disabled in this demo.')
    }, 1000)
  }

  return (
    <div className="flex items-center justify-center min-h-[70vh]">
      <Card className="w-full max-w-md">
        <CardHeader className="space-y-1 text-center">
          <CardTitle className="text-2xl font-bold">Create an Account</CardTitle>
          <CardDescription>
            Enter your information to register for the clinic
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name" className={error ? "text-destructive" : ""}>Full Name</Label>
              <Input 
                id="name" 
                placeholder="John Doe"
                value={name}
                onChange={(e: any) => setName(e.target.value)}
                className={error ? "border-destructive focus-visible:ring-destructive" : ""}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email" className={error ? "text-destructive" : ""}>Email</Label>
              <Input 
                id="email" 
                type="email" 
                placeholder="john@example.com"
                value={email}
                onChange={(e: any) => setEmail(e.target.value)}
                className={error ? "border-destructive focus-visible:ring-destructive" : ""}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className={error ? "text-destructive" : ""}>Password</Label>
              <Input 
                id="password" 
                type="password"
                value={password}
                onChange={(e: any) => setPassword(e.target.value)}
                className={error ? "border-destructive focus-visible:ring-destructive" : ""}
              />
            </div>

            {error && (
              <div className="text-sm font-medium text-destructive mt-2">
                {error}
              </div>
            )}

            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? 'Registering...' : 'Register'}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex flex-col items-center justify-center space-y-2">
          <div className="text-sm text-slate-500">
            Already have an account?{' '}
            <Link to="/login" className="text-primary hover:underline font-medium">
              Sign in
            </Link>
          </div>
        </CardFooter>
      </Card>
    </div>
  )
}
