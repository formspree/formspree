/** @format */

const render = require('react-dom').render
const React = require('react') // eslint-disable-line no-unused-vars

import Dashboard from './Dashboard'

if (document.querySelector('body.dashboard')) {
  if (location.pathname !== '/plan') {
    let fmi = document.getElementById('forms-menu-item')
    let ami = document.getElementById('account-menu-item')
    if (fmi) fmi.innerHTML = ''
    if (ami) ami.innerHTML = ''
  }

  let el = document.getElementById('react-app')
  render(<Dashboard />, el)
}
