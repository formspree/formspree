/** @format */

const render = require('react-dom').render
const React = require('react') // eslint-disable-line no-unused-vars

const Dashboard = require('./Dashboard')

if (document.querySelector('body.forms.dashboard')) {
  document.querySelector('.menu .item:nth-child(2)').innerHTML = ''
  render(<Dashboard />, document.querySelector('.container.block'))
}
