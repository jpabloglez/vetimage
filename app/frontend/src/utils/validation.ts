import { z } from 'zod';

// Common validation schemas
export const emailSchema = z
  .string()
  .min(1, 'Email is required')
  .email('Please enter a valid email address');

export const passwordSchema = z
  .string()
  .min(8, 'Password must be at least 8 characters long')
  .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
  .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
  .regex(/[0-9]/, 'Password must contain at least one number')
  .regex(/[^A-Za-z0-9]/, 'Password must contain at least one special character');

export const nameSchema = z
  .string()
  .min(2, 'Name must be at least 2 characters long')
  .max(50, 'Name must be less than 50 characters')
  .regex(/^[a-zA-Z\s]+$/, 'Name can only contain letters and spaces');

// Login form validation
export const loginSchema = z.object({
  email: emailSchema,
  password: z.string().min(1, 'Password is required'),
  rememberMe: z.boolean().optional(),
});

export type LoginFormData = z.infer<typeof loginSchema>;

// Registration form validation
export const registrationSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
  confirmPassword: z.string(),
  name: nameSchema,
  role: z.enum(['doctor', 'researcher', 'admin', 'user'], {
    required_error: 'Please select a role',
  }),
  institution: z.string().optional(),
  specialization: z.string().optional(),
  terms: z.boolean().refine((val) => val === true, {
    message: 'You must agree to the terms and conditions',
  }),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
});

export type RegistrationFormData = z.infer<typeof registrationSchema>;

// Forgot password form validation
export const forgotPasswordSchema = z.object({
  email: emailSchema,
});

export type ForgotPasswordFormData = z.infer<typeof forgotPasswordSchema>;

// Reset password form validation
export const resetPasswordSchema = z.object({
  password: passwordSchema,
  confirmPassword: z.string(),
}).refine((data) => data.password === data.confirmPassword, {
  message: 'Passwords do not match',
  path: ['confirmPassword'],
});

export type ResetPasswordFormData = z.infer<typeof resetPasswordSchema>;

// Profile update validation
export const profileUpdateSchema = z.object({
  name: nameSchema,
  institution: z.string().optional(),
  specialization: z.string().optional(),
});

export type ProfileUpdateFormData = z.infer<typeof profileUpdateSchema>;

// Medical image upload validation
export const imageUploadSchema = z.object({
  files: z.array(z.instanceof(File)).min(1, 'Please select at least one file'),
  description: z.string().optional(),
  patientAge: z.number().min(0).max(150).optional(),
  patientSex: z.enum(['male', 'female', 'other']).optional(),
  clinicalNotes: z.string().optional(),
});

export type ImageUploadFormData = z.infer<typeof imageUploadSchema>;

// ---------------------------------------------------------------------------
// Veterinary patient forms (Owner / AnimalPatient / VHS)
// ---------------------------------------------------------------------------

export const ownerSchema = z.object({
  first_name: z.string().trim().min(1, 'First name is required').max(100),
  last_name: z.string().trim().min(1, 'Last name is required').max(100),
  email: z.string().trim().min(1, 'Email is required').email('Please enter a valid email address'),
  phone: z.string().trim().min(1, 'Phone is required').refine(
    (v) => /^[+()\-\s0-9]{6,20}$/.test(v),
    'Please enter a valid phone number',
  ),
  address: z.string().max(255).optional(),
  city: z.string().max(100).optional(),
  country: z.string().max(100).optional(),
});

export type OwnerFormData = z.infer<typeof ownerSchema>;

const SPECIES = ['canine', 'feline', 'equine', 'bovine', 'avian', 'exotic', 'other'] as const;

// Minimal animal schema used only during new-owner registration (name + species required, breed optional).
export const ownerAnimalSchema = z.object({
  name: z.string().trim().min(1, 'Animal name is required').max(100),
  species: z.enum(SPECIES),
  breed: z.string().max(100).optional(),
});

export type OwnerAnimalFormData = z.infer<typeof ownerAnimalSchema>;
const SEXES = ['', 'M', 'F', 'MN', 'FS', 'U'] as const;

export const animalPatientSchema = z.object({
  name: z.string().trim().min(1, 'Patient name is required').max(100),
  species: z.enum(SPECIES),
  breed: z.string().max(100).optional(),
  sex: z.enum(SEXES).optional(),
  date_of_birth: z
    .string()
    .optional()
    .refine((v) => !v || new Date(v) <= new Date(), 'Date of birth cannot be in the future'),
  weight_kg: z
    .union([z.string(), z.number()])
    .optional()
    .refine((v) => {
      if (v === '' || v === undefined || v === null) return true;
      const n = Number(v);
      return Number.isFinite(n) && n > 0 && n < 2000;
    }, 'Enter a weight between 0 and 2000 kg'),
  // Microchip is optional; if present, ISO 11784/11785 is 15 digits.
  microchip_id: z
    .string()
    .optional()
    .refine((v) => !v || /^\d{15}$/.test(v) || /^[A-Za-z0-9]{9,20}$/.test(v),
      'Microchip should be 15 digits (ISO) or a 9–20 char alphanumeric ID'),
  color: z.string().max(100).optional(),
});

export type AnimalPatientFormData = z.infer<typeof animalPatientSchema>;

export const vhsSchema = z.object({
  measured_on: z
    .string()
    .min(1, 'Date is required')
    .refine((v) => new Date(v) <= new Date(), 'Date cannot be in the future'),
  long_axis_vertebrae: z.coerce.number().gt(0, 'Required').lte(15, 'Implausibly large'),
  short_axis_vertebrae: z.coerce.number().gt(0, 'Required').lte(15, 'Implausibly large'),
  notes: z.string().optional(),
});

export type VHSFormData = z.infer<typeof vhsSchema>;

// ---------------------------------------------------------------------------
// Clinical visit
// ---------------------------------------------------------------------------

const VISIT_TYPES = ['consultation', 'follow_up', 'vaccination', 'surgery', 'imaging', 'emergency'] as const;

export const clinicalVisitSchema = z.object({
  visit_date: z.string().min(1, 'Date and time are required'),
  visit_type: z.enum(VISIT_TYPES),
  chief_complaint: z.string().max(500).optional(),
  subjective: z.string().optional(),
  objective: z.string().optional(),
  assessment: z.string().optional(),
  plan: z.string().optional(),
  weight_kg: z.coerce.number().gt(0).lte(2000).optional().nullable(),
  temperature_celsius: z.coerce
    .number()
    .gt(30, 'Must be > 30 °C')
    .lte(45, 'Must be ≤ 45 °C')
    .optional()
    .nullable(),
  heart_rate_bpm: z.coerce.number().int().gt(0).lte(400).optional().nullable(),
  respiratory_rate: z.coerce.number().int().gt(0).lte(100).optional().nullable(),
});

export type ClinicalVisitFormData = z.infer<typeof clinicalVisitSchema>;

// ---------------------------------------------------------------------------
// Vaccination record
// ---------------------------------------------------------------------------

export const vaccinationSchema = z.object({
  vaccine_name: z.string().trim().min(1, 'Vaccine name is required').max(200),
  administered_on: z
    .string()
    .min(1, 'Date is required')
    .refine((v) => new Date(v) <= new Date(), 'Cannot be in the future'),
  next_due_on: z.string().optional().nullable(),
  batch_number: z.string().max(100).optional(),
  notes: z.string().optional(),
});

export type VaccinationFormData = z.infer<typeof vaccinationSchema>;

// ---------------------------------------------------------------------------
// Weight record
// ---------------------------------------------------------------------------

export const weightRecordSchema = z.object({
  measured_on: z.string().min(1, 'Date is required'),
  weight_kg: z.coerce.number().gt(0, 'Weight is required').lte(2000, 'Max 2000 kg'),
  bcs: z.coerce.number().int().min(1, 'Min 1').max(9, 'Max 9').optional().nullable(),
  notes: z.string().optional(),
});

export type WeightRecordFormData = z.infer<typeof weightRecordSchema>;

// ---------------------------------------------------------------------------
// Appointment
// ---------------------------------------------------------------------------

export const appointmentSchema = z.object({
  appointment_type: z.enum(VISIT_TYPES),
  scheduled_at: z.string().min(1, 'Date and time are required'),
  duration_minutes: z.coerce.number().int().min(5).max(480).optional(),
  notes: z.string().max(2000).optional(),
});

export type AppointmentFormData = z.infer<typeof appointmentSchema>;

// ---------------------------------------------------------------------------
// Prescription
// ---------------------------------------------------------------------------

export const prescriptionSchema = z.object({
  medication_name: z.string().trim().min(1, 'Medication name is required').max(200),
  prescribed_on: z.string().min(1, 'Date is required')
    .refine((v) => new Date(v) <= new Date(), 'Cannot be in the future'),
  dose: z.string().max(100).optional(),
  route: z.string().max(20).optional(),
  frequency: z.string().max(100).optional(),
  duration_days: z.coerce.number().int().gt(0).optional().nullable(),
  notes: z.string().optional(),
});

export type PrescriptionFormData = z.infer<typeof prescriptionSchema>;

// ---------------------------------------------------------------------------
// Allergy record
// ---------------------------------------------------------------------------

const ALLERGEN_TYPES = ['drug', 'food', 'environmental', 'contact'] as const;
const ALLERGY_SEVERITIES = ['mild', 'moderate', 'severe', 'life_threatening'] as const;

export const allergySchema = z.object({
  allergen: z.string().trim().min(1, 'Allergen is required').max(200),
  allergen_type: z.enum(ALLERGEN_TYPES),
  severity: z.enum(ALLERGY_SEVERITIES),
  reaction: z.string().max(1000).optional(),
  first_observed: z.string().optional().nullable(),
});

export type AllergyFormData = z.infer<typeof allergySchema>;

// ---------------------------------------------------------------------------
// Lab result
// ---------------------------------------------------------------------------

const LAB_TYPES = ['hematology', 'biochemistry', 'urinalysis', 'cytology', 'serology', 'microbiology', 'other'] as const;

export const labResultSchema = z.object({
  result_type: z.enum(LAB_TYPES),
  panel_name: z.string().trim().min(1, 'Panel name is required').max(200),
  result_date: z.string().min(1, 'Date is required'),
  lab_name: z.string().max(200).optional(),
});

export type LabResultFormData = z.infer<typeof labResultSchema>;

// ---------------------------------------------------------------------------
// Study share link
// ---------------------------------------------------------------------------

export const studyShareSchema = z.object({
  expires_at: z.string().optional().nullable(),
  max_accesses: z.coerce.number().int().gt(0).optional().nullable(),
  recipient_email: z.string().email().optional().or(z.literal('')),
});

export type StudyShareFormData = z.infer<typeof studyShareSchema>;

// ---------------------------------------------------------------------------
// Reproductive event
// ---------------------------------------------------------------------------

const REPRO_EVENT_TYPES = [
  'heat', 'mating', 'pregnancy_confirmed', 'whelping',
  'litter_registration', 'spay_neuter', 'other',
] as const;

export const reproductiveEventSchema = z.object({
  event_type: z.enum(REPRO_EVENT_TYPES),
  event_date: z
    .string()
    .min(1, 'Date is required')
    .refine((v) => new Date(v) <= new Date(), 'Cannot be in the future'),
  partner_id: z.string().max(100).optional(),
  litter_count: z.coerce.number().int().min(0).max(30).optional().nullable(),
  notes: z.string().optional(),
});

export type ReproductiveEventFormData = z.infer<typeof reproductiveEventSchema>;

/**
 * Validate data against a zod schema, returning a flat field→message map
 * ({} when valid). Lets controlled forms show inline errors without
 * react-hook-form boilerplate.
 */
export function zodFieldErrors(schema: z.ZodTypeAny, data: unknown): Record<string, string> {
  const result = schema.safeParse(data);
  if (result.success) return {};
  const errs: Record<string, string> = {};
  for (const issue of result.error.issues) {
    const key = String(issue.path[0] ?? '_');
    if (!errs[key]) errs[key] = issue.message;
  }
  return errs;
}