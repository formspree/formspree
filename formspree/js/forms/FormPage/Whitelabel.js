/** @format */

const toastr = window.toastr
const fetch = window.fetch
const React = require('react')
const CodeMirror = require('react-codemirror2')
require('codemirror/mode/xml/xml')
require('codemirror/mode/css/css')

const FormDescription = require('./FormDescription')

module.exports = class FormSettings extends React.Component {
  constructor(props) {
    super(props)

    this.changeFrom = this.changeFrom.bind(this)
    this.changeSubject = this.changeSubject.bind(this)
    this.changeStyle = this.changeStyle.bind(this)
    this.changeBody = this.changeBody.bind(this)
    this.preview = this.preview.bind(this)
    this.closePreview = this.closePreview.bind(this)
    this.revert = this.revert.bind(this)
    this.deploy = this.deploy.bind(this)

    this.defaultValues = {
      from: 'Team Formspree',
      subject: 'New submission from {{ host }}',
      style: `h1 {
  color: black;
}
.content {
  font-size: 20pt;
}`,
      body: `<div class="content">
  <h1>You've got a new submissions from {{ _replyto }}</h1>

  <table>
    {{# _fields }}
    <tr>
      <th>{{ field_name }}</th>
      <td>{{ field_value }}</td>
    </tr>
    {{/ _fields }}
  </table>
</div>`
    }

    this.state = {
      previewing: null,
      changes: {}
    }
  }

  render() {
    let {form} = this.props

    let {from, subject, style, body} = {
      ...this.defaultValues,
      ...form.template,
      ...this.state.changes
    }

    return (
      <>
        <div className="col-1-1" id="whitelabel">
          <FormDescription prefix="Whitelabel settings for" form={form} />
          <div className="container">
            <div className="col-1-6">
              <label htmlFor="from">From</label>
            </div>
            <div className="col-5-6">
              <input id="from" onChange={this.changeFrom} value={from} />
            </div>
          </div>
          <div className="container">
            <div className="col-1-6">
              <label htmlFor="subject">Subject</label>
            </div>
            <div className="col-5-6">
              <input
                id="subject"
                onChange={this.changeSubject}
                value={subject}
              />
              <div className="right">
                Overrides <span className="code">_subject</span> field
              </div>
            </div>
          </div>
          <div className="container">
            <div className="col-1-1">
              <label>
                Style
                <CodeMirror.Controlled
                  value={style}
                  options={{
                    theme: 'oceanic-next',
                    mode: 'css',
                    viewportMargin: Infinity
                  }}
                  onBeforeChange={this.changeStyle}
                />
              </label>
            </div>
          </div>
          <div className="container">
            <div className="col-1-1">
              <label>
                Body
                <CodeMirror.Controlled
                  value={body}
                  options={{
                    theme: 'oceanic-next',
                    mode: 'xml',
                    viewportMargin: Infinity
                  }}
                  onBeforeChange={this.changeBody}
                />
              </label>
            </div>
          </div>
          <div className="container">
            <div className="col-1-6">
              <button onClick={this.preview}>Preview</button>
            </div>
            <div className="col-2-6" />
            <div className="col-1-6">
              {Object.keys(this.state.changes).length > 0
                ? 'changes pending'
                : null}
            </div>
            <div className="col-1-6">
              <button
                onClick={this.revert}
                disabled={Object.keys(this.state.changes).length > 0}
              >
                Revert
              </button>
            </div>
            <div className="col-1-6">
              <button
                onClick={this.deploy}
                disabled={Object.keys(this.state.changes).length > 0}
              >
                Deploy
              </button>
            </div>
          </div>
        </div>
      </>
    )
  }

  changeFrom(e) {
    let value = e.target.value
    this.setState(state => {
      state.changes.from = value
      return state
    })
  }

  changeSubject(e) {
    let value = e.target.value
    this.setState(state => {
      state.changes.subject = value
      return state
    })
  }

  changeStyle(_, __, value) {
    this.setState(state => {
      state.changes.style = value
      return state
    })
  }

  changeBody(_, __, value) {
    this.setState(state => {
      state.changes.body = value
      return state
    })
  }

  closePreview() {
    this.setState({previewing: null})
  }

  async preview() {
    let template = {
      ...this.defaultValues,
      ...this.props.form.template,
      ...this.state.changes
    }

    try {
      let resp = await fetch('/api-int/forms/whitelabel/preview', {
        method: 'POST',
        body: JSON.stringify(template),
        credentials: 'same-origin',
        headers: {
          Accept: 'text/html',
          'Content-Type': 'application/json'
        }
      })
      let html = await resp.text()

      this.setState({previewing: html})
    } catch (e) {
      console.error(e)
      toastr.error(
        'Failed to see render preview. See the console for more details.'
      )
    }
  }

  revert() {}
  deploy() {}
}
