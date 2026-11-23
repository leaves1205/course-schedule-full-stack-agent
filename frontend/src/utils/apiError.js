// Decide what a failed HTTP request means for the caller. Kept free of UI and router imports
// so it can be unit tested.
//
// The backend answers every failure with a real HTTP status and the standard envelope
// { code, message, data }. Views read `res.code` instead of catching, so a failure that carries
// the envelope resolves with it after the user has been told. Session expiry still rejects:
// the user is sent to the login page and nothing downstream should continue.

/**
 * @param {*} err an Axios error
 * @param {{ notify: (message: string) => void, onSessionExpired: () => void }} handlers
 * @returns {{ resolve: object } | { reject: * }}
 */
export function settleFailedRequest(err, { notify, onSessionExpired }) {
  const response = err.response
  if (!response) {
    // The backend is unavailable or a network error occurred.
    notify('Network error. Check the backend service.')
    return { reject: err }
  }
  if (response.status === 401) {
    notify('Your session has expired. Please sign in again.')
    onSessionExpired()
    return { reject: err }
  }
  const body = response.data
  notify(body?.message || 'Request failed')
  if (body && typeof body.code === 'number') {
    return { resolve: body }
  }
  return { reject: err }
}
