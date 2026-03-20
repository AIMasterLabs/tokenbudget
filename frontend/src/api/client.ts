// Copyright 2026 Harsha Krishne Gowda
// SPDX-License-Identifier: Apache-2.0

import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? ''

export const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

apiClient.interceptors.request.use((config) => {
  // JWT takes priority over API key
  const jwt = localStorage.getItem('tb_token')
  const apiKey = localStorage.getItem('tb_api_key')
  const token = jwt || apiKey
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('tb_token')
      localStorage.removeItem('tb_api_key')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)
