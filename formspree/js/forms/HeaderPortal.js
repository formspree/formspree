/** @format */

const createPortal = require('react-dom').createPortal

module.exports = function TitlePortal(props) {
  return createPortal(props.children, document.querySelector('#header .center'))
}
