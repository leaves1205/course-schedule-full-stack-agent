import assert from 'node:assert/strict'
import test from 'node:test'
import { USERNAME_PATTERN, newPasswordRule, passwordProblem } from '../src/utils/passwordRules.js'

// These cases mirror backend/tests/test_hardening.py so the two policies cannot drift apart silently.
test('rejects passwords the backend would reject', () => {
  const tooLongInBytes = 'a1' + '密'.repeat(24) // 26 characters, 74 UTF-8 bytes
  for (const password of ['short1', 'lettersonly', '12345678', 'a1'.repeat(40), tooLongInBytes, '', undefined]) {
    assert.notEqual(passwordProblem(password), '', `expected a problem for ${String(password).slice(0, 12)}`)
  }
})

test('accepts a password with letters and digits of acceptable length', () => {
  assert.equal(passwordProblem('Passw0rd123'), '')
  assert.equal(passwordProblem('a'.repeat(71) + '1'), '') // exactly 72 bytes
})

test('counts characters the way the backend does', () => {
  // Seven emoji plus one digit are 8 characters (code points) even though JS length says 15.
  assert.equal(passwordProblem('😀'.repeat(7) + '1'), 'Password must contain at least one letter and one digit.')
  assert.match(passwordProblem('a1'), /at least 8 characters/)
})

test('the form rule reports the same message through the validator callback', () => {
  const results = []
  newPasswordRule.validator({}, '12345678', (error) => results.push(error))
  newPasswordRule.validator({}, 'Passw0rd123', (error) => results.push(error))
  assert.equal(results[0].message, 'Password must contain at least one letter and one digit.')
  assert.equal(results[1], undefined)
})

test('username pattern matches the backend format', () => {
  for (const name of ['abc', 'alice.smith', 'demo_admin-2026', 'x'.repeat(50)]) assert.ok(USERNAME_PATTERN.test(name), name)
  for (const name of ['ab', 'has space', 'x'.repeat(51), 'semi;colon', '']) assert.ok(!USERNAME_PATTERN.test(name), name)
})
