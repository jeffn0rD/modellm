APPLICATION SPECIFICATION

**Project:** Capital Tree Nuts Contract Management System
**Domain:** `capitaltreenuts.com`
**Version:** 0.1.0
**Date:** March 2, 2026


1. Executive Summary

A web-based application to manage, track, and execute purchase and sale contracts for Capital Tree Nuts. The system provides role-based access for Customers, Employees, and Administrators. It serves as a centralized dashboard for contract lifecycle management, including matching purchases to sales, and integrates with DocuSign for external contract execution.


2. Architecture & Technology Stack
• **Frontend Hosting:** Cloudflare Pages (`dashboard.capitaltreenuts.com` / `dev.capitaltreenuts.com`)
• **Frontend Framework:** Astro (Routing/Layout) + Svelte 5 (Reactivity) + Shadcn-Svelte (UI Components)
• **Backend Hosting:** Railway (`api.dashboard...` / `api.dev...`)
• **Backend Framework:** Node.js / Fastify
• **Database & Storage:** Supabase (PostgreSQL + Object Storage)
• **Authentication:** Supabase Auth (Email/Password)
• **External Integrations:** DocuSign API (Contract execution/status tracking)
• **Version Control:** GitHub (Monorepo structure)


⸻


3. Phase 0: Foundation & Authentication 

**Goal:** Establish the repository, CI/CD pipelines, basic UI scaffolding, user authentication, and the foundational auditing system.


3.1 Infrastructure & Repository Setup
• **Repo Structure:** Initialize a GitHub monorepo containing `/frontend` and `/backend` directories.
• **Environments:** 
*   Configure `dev` branch to deploy to `dev.capitaltreenuts.com` (Cloudflare) and `api.dev.capitaltreenuts.com` (Railway).
*   Provision a `dev` Supabase project.
• **CORS:** Configure Fastify to accept requests strictly from the designated frontend domains.


3.2 Authentication & Authorization System
• **Supabase Auth:** Implement standard Email/Password registration and login.
• **Role Management:** 
*   Create a `user_roles` table in Supabase (or utilize Supabase Custom Claims) to assign roles: `Admin`, `Employee`, `Customer`.
*   Default new registrations to a pending/unassigned state or `Customer` role (pending client clarification).
• **Frontend UI (Svelte/Shadcn):**
*   Implement a blank, branded layout shell (Header, Sidebar, Main Content Area).
*   Create `/login`, `/register`, and `/forgot-password` routes.
*   Create a protected `/dashboard` route that requires an active session to view.
• **Backend Protection:** Implement Fastify middleware to verify Supabase JWTs on all API routes.


3.3 Auditing & Logging Architecture
• **Application Logging (Backend):** Implement `pino` in Fastify for high-performance, structured JSON logging of all API requests and errors.
• **Business Event Auditing (Database):** 
*   Create an `audit_logs` table in Supabase.
*   **Schema:** `id`, `timestamp`, `actor_id` (User UUID), `action` (e.g., 'USER_LOGIN', 'CONTRACT_CREATED'), `entity_type` (e.g., 'Auth', 'Contract'), `entity_id`, `metadata` (JSONB for before/after state).
*   Implement a Fastify service/utility to easily write to this table whenever a state-changing action occurs.


⸻


4. Detail Refinement & Client Inquiry (Pending Approval)

*The following items require clarification from the client/management before data modeling and Phase 1 (Contracts) can begin.*


4.1 Contract Data Model
1. **Contract Fields:** What specific data points define a contract? *(e.g., Commodity type, weight/quantity, price, delivery dates, terms).*
2. **Purchase vs. Sale:** Do Purchase contracts and Sale contracts share the exact same fields, or do they require different data structures?
3. **The "Closing/Matching" Mechanism:** How are purchases attached to sales? 
*   Is it 1-to-1 (One purchase fulfills one sale)? 
*   Is it 1-to-Many (One large purchase is split to fulfill multiple smaller sales)?


4.2 DocuSign Integration
1. **Trigger Point:** At what stage is a contract sent to DocuSign? *(e.g., Created by employee -> Sent to Customer via DocuSign -> Customer signs -> Status updates to 'Active').*
2. **Document Generation:** Will the system generate the PDF to send to DocuSign, or are users uploading pre-made PDFs to send?
3. **Signers:** Who needs to sign? Just the customer, or does an internal employee/admin need to counter-sign?


4.3 User Roles & Workflows
1. **Customer Entity:** Is a "Customer" an individual person, or a "Company" that might have multiple employee logins associated with it?
2. **Customer Onboarding:** Can customers register themselves freely, or must an Admin/Employee invite them to the platform?
3. **Visibility:** Can Employees see and edit *all* contracts, or only ones specifically assigned to them?
4. **Dashboards:** What are the top 2-3 things a Customer needs to see immediately upon logging in? What about an Employee?


4.4 Auditing Specifics
1. **Audit Scope:** Does the client require strict "Event Sourcing" (tracking every single keystroke/field change on a contract), or is tracking major lifecycle events (Created, Sent for Signature, Signed, Closed, Deleted) sufficient?