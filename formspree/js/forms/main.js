/** @format */

const render = require('react-dom').render
const React = require('react') // eslint-disable-line no-unused-vars
const Modal = require('react-modal')

const Dashboard = require('./Dashboard')

if (document.querySelector('body.forms.dashboard')) {
  let el = document.querySelector('.container.block')
  Modal.setAppElement(el)

  document.querySelector('.menu .item:nth-child(2)').innerHTML = ''
  render(<Dashboard />, el)
}
