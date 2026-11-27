# Patient Portal (Module 4.2) — Architecture & Concepts Summary

This document summarizes the approach, logic, and core features implemented in the Patient Portal module for the Clinic Appointment Manager.

## 1. Overview & Core Features

The Patient Portal is the primary interface for patients to interact with the clinic. It provides a secure, self-service dashboard (`PatientDashboard.tsx`) that allows patients to manage their entire lifecycle with the clinic, from booking appointments to reviewing past visits and downloading receipts.

Key features include:
- **Comprehensive Appointment Dashboard:** Separate views for "Upcoming Appointments" and "Past Visits" using a tabbed interface.
- **Self-Service Booking Engine:** A robust, concurrent-safe booking flow allowing patients to select available dates, view open slots, and confirm appointments.
- **Appointment Cancellations:** Secure cancellation flows with explicit user confirmation (via `AlertDialog`) to prevent accidental cancellations.
- **Billing Transparency:** Read-only access to invoices for paid visits, including a direct "Download Receipt" action.

## 2. Secure Booking & Concurrency

When patients book appointments, there is a risk of a "double-booking" race condition if two patients attempt to book the exact same slot concurrently. 

**How we solved it:**
- **Real-Time Slot Fetching:** The booking modal queries the backend dynamically for available slots for a given date, filtering out already booked times.
- **Database Constraints:** The backend enforces a composite unique constraint (`doctor_id`, `scheduled_time`) at the database layer. If a race condition occurs, the database throws an `IntegrityError`, which the backend intercepts and translates into a user-friendly `409 Conflict` error, prompting the patient to select a different time.

## 3. Graceful State Management & UX

The frontend leverages React context and state to provide a seamless experience:
- **Optimistic UI Updates:** When an appointment is booked or cancelled, the local state is immediately updated, and a background refetch ensures consistency with the server.
- **Alert Dialogs for Destructive Actions:** Canceling an appointment is a destructive action. We implemented a confirmation modal (`AlertDialog`) that requires explicit intent before triggering the backend transition to the `CANCELLED` state.
- **Responsive Design:** The dashboard uses Tailwind CSS to ensure the UI is fully responsive, looking great on both desktop and mobile devices (which is critical for a patient-facing portal).

## 4. Integration with Billing & Auth

- **Authentication:** The Patient Portal is strictly protected by the Role-Based Access Control (RBAC) system. Only users with the `patient` role (authenticated via HttpOnly JWT cookies or Google SSO) can access this dashboard.
- **Receipts:** The portal integrates seamlessly with the billing module. For any appointment in the `PAID` state, patients are presented with a "Download Receipt" button that connects to the `pdf_generator.py` service on the backend to generate and serve a secure PDF receipt.
