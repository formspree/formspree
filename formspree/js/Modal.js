/** @format */

const React = require('react')
const cs = require('class-set')

export default class Modal extends React.Component {
  constructor(props) {
    super(props)

    this.close = this.close.bind(this)
  }

  render() {
    return (
      <>
        <div
          className={cs({'modal-overlay': true, open: this.props.opened})}
          onClick={this.close}
        />
        <div
          className={cs({modal: true, react: true, target: this.props.opened})}
        >
          <div className="container">
            {this.props.opened ? (
              <>
                <div className="x">
                  <h4>{this.props.title}</h4>
                  <a href="#" onClick={this.close}>
                    &times;
                  </a>
                </div>
                {this.props.children}
              </>
            ) : null}
          </div>
        </div>
      </>
    )
  }

  close(e) {
    e.preventDefault()
    this.props.onClose(e)
  }
}
