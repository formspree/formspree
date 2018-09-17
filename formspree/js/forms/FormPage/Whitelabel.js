/** @format */

const toastr = window.toastr
const fetch = window.fetch
const React = require('react')
const CodeMirror = require('react-codemirror2')
const Modal = require('react-modal')
require('codemirror/mode/xml/xml')
require('codemirror/mode/css/css')

const FormDescription = require('./FormDescription')

const MODAL_REVERT = 'revert'
const MODAL_PREVIEW = 'preview'
const MODAL_SYNTAX = 'syntax'

module.exports = class FormSettings extends React.Component {
  constructor(props) {
    super(props)

    this.changeFromName = this.changeFromName.bind(this)
    this.changeSubject = this.changeSubject.bind(this)
    this.changeStyle = this.changeStyle.bind(this)
    this.changeBody = this.changeBody.bind(this)
    this.preview = this.preview.bind(this)
    this.showSyntax = this.showSyntax.bind(this)
    this.closeModal = this.closeModal.bind(this)
    this.attemptRevert = this.attemptRevert.bind(this)
    this.revert = this.revert.bind(this)
    this.deploy = this.deploy.bind(this)

    this.defaultValues = {
      from_name: 'Team Formspree',
      subject: 'New submission from {{ host }}',
      style: `h1 {
  color: black;
}
.content {
  font-size: 15pt;
}`,
      body: `<div class="content">
  <h1>You've got a new submission from {{ _replyto }} on {{ _host }}</h1>

  <table>
    {{# _fields }}
    <tr>
      <th>{{ _name }}</th>
      <td>{{ _value }}</td>
    </tr>
    {{/ _fields }}
  </table>
</div>
<p>This submission was sent on {{ _time }}.</p>
<br>
<hr>`
    }

    this.state = {
      changes: {},
      modal: null,
      previewHTML: null
    }
  }

  render() {
    let {form} = this.props

    let {from_name, subject, style, body} = {
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
              <label htmlFor="from_name">From</label>
            </div>
            <div className="col-5-6">
              <input
                id="from_name"
                onChange={this.changeFromName}
                value={from_name}
              />
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
            <label className="row">
              <div className="col-1-1">Style</div>
              <div className="col-1-1">
                <CodeMirror.Controlled
                  value={style}
                  options={{
                    theme: 'oceanic-next',
                    mode: 'css',
                    viewportMargin: Infinity
                  }}
                  onBeforeChange={this.changeStyle}
                />
              </div>
            </label>
          </div>
          <div className="container">
            <label className="row">
              <div className="row">
                <div className="col-1-2">Body</div>
                <div className="col-1-2 right">
                  <a href="#" onClick={this.showSyntax}>
                    syntax quick reference
                  </a>
                </div>
              </div>
              <div className="col-1-1">
                <CodeMirror.Controlled
                  value={body}
                  options={{
                    theme: 'oceanic-next',
                    mode: 'xml',
                    viewportMargin: Infinity
                  }}
                  onBeforeChange={this.changeBody}
                />
              </div>
            </label>
          </div>
          <div className="container">
            <div className="col-1-6">
              <button onClick={this.preview}>Preview</button>
            </div>
            <div className="col-2-3 right">
              {Object.keys(this.state.changes).length > 0
                ? 'changes pending'
                : null}
            </div>
            <div className="col-1-6">
              <button
                onClick={this.attemptRevert}
                disabled={Object.keys(this.state.changes).length === 0}
              >
                Revert
              </button>
            </div>
            <div className="col-1-6">
              <button
                onClick={this.deploy}
                disabled={Object.keys(this.state.changes).length === 0}
              >
                Deploy
              </button>
            </div>
          </div>
        </div>
        <Modal
          contentLabel="Revert changes"
          isOpen={this.state.modal === MODAL_REVERT}
          onRequestClose={this.closeModal}
          className="dummy"
          overlayClassName="dummy"
        >
          <div>
            <div className="container">
              <h2>Are you sure?</h2>
              <p>
                Reverting will discard the changes you've made to your email
                template.
              </p>
            </div>
            <div className="container right">
              <button onClick={this.closeModal}>Cancel</button>
              <button onClick={this.revert}>Revert</button>
            </div>
          </div>
        </Modal>
        <Modal
          contentLabel="Preview"
          isOpen={this.state.modal === MODAL_PREVIEW}
          onRequestClose={this.closeModal}
          className="dummy"
          overlayClassName="dummy"
        >
          <div id="whitelabel-preview-modal">
            <div
              className="container preview"
              dangerouslySetInnerHTML={{__html: this.state.previewHTML}}
            />
            <div className="container right">
              <button onClick={this.closeModal}>OK</button>
            </div>
          </div>
        </Modal>
        <Modal
          contentLabel="Email Syntax"
          isOpen={this.state.modal === MODAL_SYNTAX}
          onRequestClose={this.closeModal}
          className="dummy"
          overlayClassName="dummy"
        >
          <div>
            <div>
              <h2>Email Syntax</h2>
              <p>
                the email body can contain simple HTML that's valid in an email.
                No <span className="code">&lt;script&gt;</span> or{' '}
                <span className="code">&lt;style&gt;</span>
                tags can be included. For a list of recommended HTML tags see{' '}
                <a href="" target="_blank">
                  the ContantContact guide to HTML in email
                </a>
                .
              </p>
              <p>
                The following special variables are recognized by Formspree,
                using the{' '}
                <a
                  href="https://mustache.github.io/mustache.5.html"
                  target="_blank"
                >
                  mustache
                </a>{' '}
                template language.
              </p>
              <pre>
                {`
{{ _time }}         The formatted date and time of the submission.
{{ _host }}         The URL (without "https://") of where the form was submitted.
{{ <fieldname> }}   Any named input value in your form will be displayed.
{{# _fields }}      A list of all fields can be included.
  {{ _name }}       Within the _fields block you can access the current field name…
  {{ _value }}      … and field value.
{{/ _fields }}      Closes the _fields block.
                `.trim()}
              </pre>
            </div>
            <div className="container right">
              <button onClick={this.closeModal}>OK</button>
            </div>
          </div>
        </Modal>
      </>
    )
  }

  changeFromName(e) {
    let value = e.target.value
    this.setState(state => {
      state.changes.from_name = value
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

  closeModal() {
    this.setState({modal: null})
  }

  async preview(e) {
    e.preventDefault()

    this.setState({modal: MODAL_PREVIEW})

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

      this.setState({previewHTML: html})
    } catch (e) {
      console.error(e)
      toastr.error(
        'Failed to see render preview. See the console for more details.'
      )
    }
  }

  attemptRevert(e) {
    e.preventDefault()

    this.setState({modal: MODAL_REVERT})
  }

  revert(e) {
    e.preventDefault()

    this.setState({changes: {}, modal: null})
  }

  showSyntax(e) {
    e.preventDefault()
    this.setState({modal: MODAL_SYNTAX})
  }

  async deploy(e) {
    e.preventDefault()

    try {
      let resp = await fetch(
        `/api-int/forms/${this.props.form.hashid}/whitelabel`,
        {
          method: 'PUT',
          body: JSON.stringify({
            ...this.defaultValues,
            ...this.props.form.template,
            ...this.state.changes
          }),
          credentials: 'same-origin',
          headers: {
            Accept: 'application/json',
            'Content-Type': 'application/json'
          }
        }
      )
      let r = await resp.json()

      if (!resp.ok || r.error) {
        toastr.warning(
          r.error
            ? `Failed to save custom template: ${r.error}`
            : 'Failed to save custom template.'
        )
        return
      }

      toastr.success('Custom template saved.')
      this.props.onUpdate().then(() => {
        this.setState({changes: {}})
      })
    } catch (e) {
      console.error(e)
      toastr.error(
        'Failed to save custom template. See the console for more details.'
      )
    }
  }
}
