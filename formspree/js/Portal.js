/** @format */

const React = require('react')
const createPortal = require('react-dom').createPortal

module.exports = class Portal extends React.Component {
  render() {
    return createPortal(
      this.props.children,
      document.querySelector(this.props.to)
    )
  }
}
