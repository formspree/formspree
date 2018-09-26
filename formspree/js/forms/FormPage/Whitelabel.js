/** @format */

const toastr = window.toastr
const fetch = window.fetch
const cs = require('class-set')
const qs = require('query-string')
const React = require('react')
const CodeMirror = require('react-codemirror2')
require('codemirror/mode/xml/xml')
require('codemirror/mode/css/css')

import Modal from '../../Modal'

const MODAL_REVERT = 'revert'
const MODAL_PREVIEW = 'preview'
const MODAL_SYNTAX = 'syntax'

export default class FormSettings extends React.Component {
  constructor(props) {
    super(props)

    this.changeFromName = this.changeFromName.bind(this)
    this.changeSubject = this.changeSubject.bind(this)
    this.changeStyle = this.changeStyle.bind(this)
    this.changeBody = this.changeBody.bind(this)
    this.preview = this.preview.bind(this)
    this.showSyntax = this.showSyntax.bind(this)
    this.closeModal = this.closeModal.bind(this)
    this.changeTab = this.changeTab.bind(this)
    this.attemptRevert = this.attemptRevert.bind(this)
    this.revert = this.revert.bind(this)
    this.deploy = this.deploy.bind(this)

    this.defaultValues = {
      from_name: 'Team Formspree',
      subject: 'New submission from {{ _host }}',
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

    this.availableTabs = ['HTML', 'CSS']

    this.state = {
      changes: {},
      modal: null,
      activeTab: 'HTML'
    }
  }

  renderSyntaxModal() {
    return (
      <>
        <Modal
          title="Email Syntax"
          opened={this.state.modal === MODAL_SYNTAX}
          onClose={this.closeModal}
        >
          <div>
            <div>
              <p>
                the email body can contain simple HTML that's valid in an email.
                No <span className="code">&lt;script&gt;</span> or{' '}
                <span className="code">&lt;style&gt;</span> tags can be{' '}
                included. For a list of recommended HTML tags see{' '}
                <a
                  href="https://explore.reallygoodemails.com/new-to-email-coding-heres-where-to-start-2494422f0bd4"
                  target="_blank"
                >
                  this guide to HTML in email
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
{{ _time }}         The date and time of the submission.
{{ _host }}         The URL of the form (without "https://").
{{ <fieldname> }}   Any named input value in your form.
{{# _fields }}      Starts a list of all fields.
  {{ _name }}       Within _fields, the current field name…
  {{ _value }}      … and field value.
{{/ _fields }}      Closes the _fields block.
                `.trim()}
              </pre>
              <div className="container right">
                <button onClick={this.closeModal}>OK</button>
              </div>
            </div>
          </div>
        </Modal>
      </>
    )
  }

  renderRevertModal() {
    return (
      <>
        <Modal
          title="Revert changes"
          opened={this.state.modal === MODAL_REVERT}
          onClose={this.closeModal}
        >
          <div>
            <div>
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
      </>
    )
  }

  renderPreviewModal(from_name, subject, style, body) {
    return (
      <>
        <Modal
          title="Preview"
          opened={this.state.modal === MODAL_PREVIEW}
          onClose={this.closeModal}
        >
          <div id="whitelabel-preview-modal">
            <iframe
              className="preview"
              src={
                '/forms/whitelabel/preview?' +
                qs.stringify({
                  from_name,
                  subject,
                  style,
                  body
                })
              }
            />
            <div className="container right">
              <button onClick={this.closeModal}>OK</button>
            </div>
          </div>
        </Modal>
      </>
    )
  }

  render() {
    let {from_name, subject, style, body} = {
      ...this.defaultValues,
      ...this.props.template,
      ...this.state.changes
    }
    var shownCode
    switch (this.state.activeTab) {
      case 'CSS':
        shownCode = (
          <CodeMirror.Controlled
            value={style}
            options={{
              theme: 'oceanic-next',
              mode: 'css',
              viewportMargin: Infinity
            }}
            onBeforeChange={this.changeStyle}
          />
        )
        break
      case 'HTML':
        shownCode = (
          <CodeMirror.Controlled
            value={body}
            options={{
              theme: 'oceanic-next',
              mode: 'xml',
              viewportMargin: Infinity
            }}
            onBeforeChange={this.changeBody}
          />
        )
    }

    return (
      <>
        <div id="whitelabel">
          <div className="container">
            <form>
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
              <div className="col-1-6">
                <label htmlFor="subject">Subject</label>
              </div>
              <div className="col-5-6">
                <input
                  id="subject"
                  onChange={this.changeSubject}
                  value={subject}
                />
                <div className="subtext">
                  Overrides <span className="code">_subject</span> field
                </div>
              </div>
            </form>
          </div>
          <div className="container">
            <div className="col-1-1 right">
              <div className="syntax_ref">
                <a href="#" onClick={this.showSyntax}>
                  syntax quick reference
                </a>
              </div>
            </div>
            {this.renderSyntaxModal()}
            <div className="col-1-1">
              <div className="code-tabs">
                {this.availableTabs.map(tabName => (
                  <div
                    key={tabName}
                    data-tab={tabName}
                    onClick={this.changeTab}
                    className={cs({active: this.state.activeTab === tabName})}
                  >
                    {tabName}
                  </div>
                ))}
              </div>
              {shownCode}
            </div>
          </div>

          <div className="container">
            {this.renderPreviewModal(from_name, subject, style, body)}
            <div className="col-1-3">
              <button onClick={this.preview}>Preview</button>
            </div>
            <div className="col-1-3 right">
              {Object.keys(this.state.changes).length > 0
                ? 'changes pending'
                : '\u00A0'}
            </div>
            <div className="col-1-6 right">
              {this.renderRevertModal()}
              <button
                onClick={this.attemptRevert}
                disabled={Object.keys(this.state.changes).length === 0}
              >
                Revert
              </button>
            </div>
            <div className="col-1-6 right">
              <button
                onClick={this.deploy}
                disabled={Object.keys(this.state.changes).length === 0}
              >
                Deploy
              </button>
            </div>
          </div>
        </div>        
      </>
    )
  }

  changeTab(e) {
    e.preventDefault()
    this.setState({activeTab: e.target.dataset.tab})
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
