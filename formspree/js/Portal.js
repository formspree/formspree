/** @format */

const React = require('react')
const createPortal = require('react-dom').createPortal

export default class Portal extends React.Component {
  render() {
    let target = document.querySelector(this.props.to)

    if (target) {
      return createPortal(this.props.children, target)
    } else {
      return null
    }
  }
}
