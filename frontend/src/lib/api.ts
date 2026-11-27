import axios, { AxiosError } from 'axios';

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  withCredentials: true, // Crucial for HttpOnly cookies
});

// Helper to strip 'Z' from ISO date strings so the browser parses them as local time
const stripTimezones = (obj: any): any => {
  if (typeof obj === 'string') {
    // Match ISO 8601 strings ending in Z
    const isoRegex = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$/;
    if (isoRegex.test(obj)) {
      return obj.replace('Z', '');
    }
  } else if (obj instanceof Blob) {
    return obj;
  } else if (Array.isArray(obj)) {
    for (let i = 0; i < obj.length; i++) {
      obj[i] = stripTimezones(obj[i]);
    }
  } else if (obj !== null && typeof obj === 'object') {
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        obj[key] = stripTimezones(obj[key]);
      }
    }
  }
  return obj;
};

// Response interceptor for global error handling and token refresh
apiClient.interceptors.response.use(
  (response) => {
    // Strip timezones from all response data
    if (response.data) {
      response.data = stripTimezones(response.data);
    }
    return response;
  },
  async (error: AxiosError) => {
    const originalRequest = error.config;

    // Avoid infinite loops if refresh itself fails, and don't intercept login failures
    if (
      error.response?.status === 401 && 
      originalRequest && 
      !originalRequest.url?.includes('/auth/refresh') &&
      !originalRequest.url?.includes('/auth/login')
    ) {
      try {
        await axios.post(
          `${apiClient.defaults.baseURL}/auth/refresh`,
          {},
          { withCredentials: true }
        );
        // Retry original request
        return apiClient(originalRequest);
      } catch (refreshError) {
        // Dispatch an event so AuthContext can handle the logout cleanly without full page reloads
        window.dispatchEvent(new Event('auth_unauthorized'));
        return Promise.reject(refreshError);
      }
    }

    // Extract backend detail message uniformly
    if (error.response?.data && (error.response.data as any).detail) {
      error.message = (error.response.data as any).detail;
    }

    return Promise.reject(error);
  }
);

// ── Auth Endpoints ───────────────────────────────────────────────────────────
export const authApi = {
  register: (data: any) => apiClient.post('/auth/register', data).then(res => res.data),
  login: (data: any) => apiClient.post('/auth/login', data).then(res => res.data),
  logout: () => apiClient.post('/auth/logout').then(res => res.data),
  whoami: () => apiClient.get('/auth/whoami').then(res => res.data),
  refresh: () => apiClient.post('/auth/refresh').then(res => res.data),
  googleLoginUrl: () => `${apiClient.defaults.baseURL}/auth/google/login`,
};

// ── Scheduling Endpoints ─────────────────────────────────────────────────────
export const schedulingApi = {
  updateWorkingHours: (config: any) => apiClient.patch('/doctors/me/working-hours', config).then(res => res.data),
  getWorkingHours: () => apiClient.get('/doctors/me/working-hours').then(res => res.data),
  generateSlots: (doctorId: number, date: string) => apiClient.post(`/doctors/${doctorId}/slots/generate?target_date=${date}`).then(res => res.data),
  getOpenSlots: (doctorId: number, date: string) => apiClient.get(`/slots?doctor_id=${doctorId}&date=${date}`).then(res => res.data),
  bookAppointment: (slotId: number) => apiClient.post('/appointments/book', { slot_id: slotId }).then(res => res.data),
};

// ── Appointment Endpoints ────────────────────────────────────────────────────
export const appointmentApi = {
  getTodayQueue: (date?: string) => apiClient.get(date ? `/appointments/queue/today?date=${date}` : '/appointments/queue/today').then(res => res.data),
  getMyQueue: (date?: string) => apiClient.get(date ? `/appointments/queue/mine?date=${date}` : '/appointments/queue/mine').then(res => res.data),
  checkIn: (appointmentId: number) => apiClient.post(`/appointments/${appointmentId}/check-in`).then(res => res.data),
  cancel: (appointmentId: number) => apiClient.post(`/appointments/${appointmentId}/cancel`).then(res => res.data),
  startConsultation: (appointmentId: number) => apiClient.post(`/appointments/${appointmentId}/start-consultation`).then(res => res.data),
  downloadInvoice: (invoiceId: number) => apiClient.get(`/invoices/${invoiceId}/download`).then(res => res.data),
};

// ── Clinical Note Endpoints ──────────────────────────────────────────────────
export const clinicalNoteApi = {
  generateDraft: (appointmentId: number, shorthandInput: string) => 
    apiClient.post(`/appointments/${appointmentId}/clinical-note/draft`, { shorthand_input: shorthandInput }).then(res => res.data),
  finalizeNote: (appointmentId: number, data: any) => 
    apiClient.post(`/appointments/${appointmentId}/clinical-note/finalize`, data).then(res => res.data),
  completeVisit: (appointmentId: number) => 
    apiClient.post(`/appointments/${appointmentId}/complete`).then(res => res.data),
  getPatientHistory: (patientId: number) => 
    apiClient.get(`/patients/${patientId}/history`).then(res => res.data),
  downloadPrescription: (appointmentId: number) => {
    return apiClient.get(`/appointments/${appointmentId}/clinical-note/pdf`, { responseType: 'blob' })
      .then(res => {
        const url = window.URL.createObjectURL(new Blob([res.data]));
        return { url };
      });
  },
};

// ── Billing Endpoints ────────────────────────────────────────────────────────
export const billingApi = {
  createInvoice: (appointmentId: number) => apiClient.post(`/appointments/${appointmentId}/invoice`).then(res => res.data),
  createRazorpayOrder: (invoiceId: number) => apiClient.post(`/invoices/${invoiceId}/razorpay-order`).then(res => res.data),
  verifyRazorpayPayment: (invoiceId: number, data: any) => apiClient.post(`/invoices/${invoiceId}/verify-razorpay`, data).then(res => res.data),
  payCash: (invoiceId: number, amountReceived: number) => 
    apiClient.post(`/invoices/${invoiceId}/pay-cash`, { amount_received: amountReceived }).then(res => res.data),
};

// ── Receptionist Endpoints ───────────────────────────────────────────────────
export const receptionistApi = {
  walkIn: (data: any) => apiClient.post('/receptionist/walk-in', data).then(res => res.data),
  getAnalytics: () => apiClient.get('/receptionist/analytics/daily').then(res => res.data),
  getDoctors: () => apiClient.get('/doctors').then(res => res.data),
  getDoctorSlots: (doctorId: number, date: string) => apiClient.get(`/receptionist/doctors/${doctorId}/slots?date=${date}`).then(res => res.data),
};

// ── Doctor Endpoints ─────────────────────────────────────────────────────────
export const doctorApi = {
  addDoctor: (data: any) => apiClient.post('/doctors', data).then(res => res.data),
};

// ── Profile Endpoints ────────────────────────────────────────────────────────
export const profileApi = {
  getMyProfile: () => apiClient.get('/profile/me').then(res => res.data),
  updateMyProfile: (data: any) => apiClient.put('/profile/me', data).then(res => res.data),
  updatePassword: (data: any) => apiClient.put('/profile/me/password', data).then(res => res.data),
};
