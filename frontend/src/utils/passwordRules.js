// Mirrors backend/app/schemas/validators.py. The backend is the authority; these rules only give
// early feedback, so keep both in sync when either changes.
export const PASSWORD_MIN_LENGTH = 8
// bcrypt ignores everything after 72 bytes, so the backend refuses longer passwords.
export const PASSWORD_MAX_BYTES = 72
export const USERNAME_PATTERN = /^[A-Za-z0-9_.-]{3,50}$/

const encoder = new TextEncoder()

/** Return a message describing why `value` is not an acceptable new password, or '' if it is. */
export function passwordProblem(value) {
  const text = typeof value === 'string' ? value : ''
  // Spread to count code points, which is how the backend counts characters.
  if ([...text].length < PASSWORD_MIN_LENGTH) {
    return `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`
  }
  if (encoder.encode(text).length > PASSWORD_MAX_BYTES) {
    return `Password must be at most ${PASSWORD_MAX_BYTES} bytes.`
  }
  if (!/[A-Za-z]/.test(text) || !/\d/.test(text)) {
    return 'Password must contain at least one letter and one digit.'
  }
  return ''
}

/** Element Plus async-validator rule for a password that is being created or changed. */
export const newPasswordRule = {
  validator: (_rule, value, callback) => {
    const problem = passwordProblem(value)
    callback(problem ? new Error(problem) : undefined)
  },
  trigger: 'blur'
}

export const usernameRule = {
  pattern: USERNAME_PATTERN,
  message: 'Username must be 3-50 characters: letters, digits, dots, hyphens or underscores',
  trigger: 'blur'
}
