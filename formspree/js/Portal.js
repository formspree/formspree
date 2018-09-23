/** @format */

const React = require('react')
const createPortal = require('react-dom').createPortal

export default class Portal extends React.Component {
  render() {
    return createPortal(
      this.props.children,
      document.querySelector(this.props.to)
    )
  }
}
