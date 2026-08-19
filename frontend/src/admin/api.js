import { api } from '../lib/api.js'

export function getUsers() {
  return api('/admin/users')
}

export function setUserDisabled(id, disabled, password) {
  return api(`/admin/users/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ disabled, password }),
  })
}

export function deleteUser(id, password) {
  return api(`/admin/users/${id}`, {
    method: 'DELETE',
    body: JSON.stringify({ password }),
  })
}