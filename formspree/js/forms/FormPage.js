/** @format */

const toastr = window.toastr
const React = require('react')
const {Route, Link, NavLink, Redirect} = require('react-router-dom')
const CodeMirror = require('react-codemirror2')
require('codemirror/mode/xml/xml')

const Portal = require('../Portal')

module.exports = class FormPage extends React.Component {
  constructor(props) {
    super(props)

    this.state = {
      form: null
    }

    this.fetchForm = this.fetchForm.bind(this)
  }

  async componentDidMount() {
    this.fetchForm()
  }

  render() {
    let hashid = this.props.match.params.hashid

    return (
      <>
        <Portal to=".menu .item:nth-child(2)">
          <Link to="/forms">Your forms</Link>
        </Portal>
        <Portal to="#header .center">
          <h1>{hashid}</h1>
          <h3>
            <NavLink
              to={`/forms/${hashid}/submissions`}
              activeStyle={{color: 'inherit', cursor: 'normal'}}
            >
              Submission History
            </NavLink>
            <NavLink
              to={`/forms/${hashid}/settings`}
              activeStyle={{color: 'inherit', cursor: 'normal'}}
            >
              Form Settings
            </NavLink>
          </h3>
        </Portal>
        <Route
          exact
          path={`/forms/${hashid}`}
          render={() => <Redirect to={`/forms/${hashid}/submissions`} />}
        />
        {this.state.form && (
          <>
            <Route
              path="/forms/:hashid/submissions"
              render={() => (
                <FormSubmissions
                  form={this.state.form}
                  onUpdate={this.fetchForm}
                />
              )}
            />
            <Route
              path="/forms/:hashid/settings"
              render={() => (
                <FormSettings
                  form={this.state.form}
                  history={this.props.history}
                  onUpdate={this.fetchForm}
                />
              )}
            />
          </>
        )}
      </>
    )
  }

  async fetchForm() {
    let hashid = this.props.match.params.hashid

    try {
      let r = await (await fetch(`/api/forms/${hashid}`, {
        credentials: 'same-origin',
        headers: {Accept: 'application/json'}
      })).json()

      this.setState({form: r})
    } catch (e) {
      console.error(e)
      toastr.error(`Failed to fetch form, see the console for more details.`)
    }
  }
}

class FormSubmissions extends React.Component {
  constructor(props) {
    super(props)

    this.deleteSubmission = this.deleteSubmission.bind(this)
    this.showExportButtons = this.showExportButtons.bind(this)

    this.state = {
      exporting: false
    }
  }

  render() {
    let {form} = this.props

    return (
      <div className="col-1-1 submissions-col">
        <h2>
          Submissions for
          {!form.hash ? (
            <span className="code">/{form.hashid}</span>
          ) : (
            <span className="code">/{form.email}</span>
          )}
          on <span className="code">{form.host}</span>
          {form.sitewide ? 'and all its subpaths.' : null}
          {form.hash ? (
            <>
              <br />
              <small>
                you can now replace the email in the URL with{' '}
                <span className="code">{`/${form.hashid}`}</span>
              </small>
            </>
          ) : (
            <>
              <br />
              <small>
                targeting <span className="code">{form.email}</span>
              </small>
            </>
          )}
        </h2>
        {form.submissions.length ? (
          <>
            <table className="submissions responsive">
              <thead>
                <tr>
                  <th>Submitted at</th>
                  {form.fields
                    .slice(1 /* the first field is 'date' */)
                    .map(f => (
                      <th key={f}>{f}</th>
                    ))}
                  <th />
                </tr>
              </thead>
              <tbody>
                {form.submissions.map(s => (
                  <tr id={`submission-${s.id}`} key={s.id}>
                    <td id={`p-${s.id}`} data-label="Submitted at">
                      {new Date(Date.parse(s.date))
                        .toString()
                        .split(' ')
                        .slice(0, 5)
                        .join(' ')}
                    </td>
                    {form.fields
                      .slice(1 /* the first field is 'date' */)
                      .map(f => (
                        <td data-label={f} key={f}>
                          <pre>{s[f]}</pre>
                        </td>
                      ))}
                    <td>
                      <button
                        className="no-border"
                        data-sub={s.id}
                        onClick={this.deleteSubmission}
                      >
                        <i className="fa fa-trash-o delete" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="container">
              <div className="row">
                {this.state.exporting ? (
                  <div className="col-1-1 right">
                    <a
                      target="_blank"
                      className="button"
                      style={{marginRight: '5px'}}
                      href={`/forms/${form.hashid}.json`}
                    >
                      Export as JSON
                    </a>
                    <a
                      target="_blank"
                      className="button"
                      href={`/forms/${form.hashid}.csv`}
                    >
                      Export as CSV
                    </a>
                  </div>
                ) : (
                  <div className="col-1-1 right">
                    <button
                      onClick={this.showExportButtons}
                      href={`/forms/${form.hashid}.json`}
                    >
                      Export
                    </button>
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <h3>No submissions archived yet.</h3>
        )}
      </div>
    )
  }

  showExportButtons(e) {
    e.preventDefault()
    this.setState({exporting: true})
  }

  async deleteSubmission(e) {
    e.preventDefault()

    let subid = e.currentTarget.dataset.sub

    try {
      let r = await (await fetch(
        `/api/forms/${this.props.form.hashid}/submissions/${subid}`,
        {
          method: 'DELETE',
          credentials: 'same-origin',
          headers: {Accept: 'application/json'}
        }
      )).json()

      if (r.error) {
        toastr.warning(`Failed to delete submission: ${r.error}`)
        return
      }

      toastr.success('Submission deleted.')
      this.props.onUpdate()
    } catch (e) {
      console.error(e)
      toastr.error(
        'Failed to delete submission, see the console for more details.'
      )
    }
  }
}

class FormSettings extends React.Component {
  constructor(props) {
    super(props)

    this.update = this.update.bind(this)
    this.deleteForm = this.deleteForm.bind(this)
    this.cancelDelete = this.cancelDelete.bind(this)

    this.state = {
      deleting: false
    }
  }

  render() {
    let {form} = this.props

    return (
      <>
        <div className="col-1-1" id="settings">
          <h2>Sample HTML</h2>
          <div className="container">
            <div className="row">
              <div className="col-1-1">
                <p>
                  Use this code in your HTML, modifying it according to your
                  needs:
                </p>
                <CodeMirror.UnControlled
                  value={`<form
  action="${form.url}"
  method="POST"
>
  <label>
    Your email:
    <input type="text" name="_replyto">
  </label>
  <label>
    Your message:
    <textarea name="message"></textarea>
  </label>

  <!-- your other form fields go here -->

  <button type="submit">Send</button>
</form>`}
                  options={{
                    theme: 'oceanic-next',
                    mode: 'xml',
                    viewportMargin: Infinity
                  }}
                />
              </div>
            </div>
          </div>
        </div>
        <div className="col-1-1" id="settings">
          <h2>Form Settings</h2>
          <div className="container">
            <div className="row">
              <div className="col-5-6">
                <h4>Form Enabled</h4>
                <p className="description">
                  You can disable this form to cause it to stop receiving new
                  submissions temporarily or permanently.
                </p>
              </div>
              <div className="col-1-6 switch-row">
                <label className="switch">
                  <input
                    type="checkbox"
                    onChange={this.update}
                    checked={!form.disabled}
                    name="disabled"
                  />
                  <span className="slider" />
                </label>
              </div>
            </div>
            <div className="row">
              <div className="col-5-6">
                <div>
                  <h4>reCAPTCHA</h4>
                </div>
                <p className="description">
                  reCAPTCHA provides vital spam protection, but you can turn it
                  off if you need.
                </p>
              </div>
              <div className="col-1-6 switch-row">
                <div>
                  <label className="switch">
                    <input
                      type="checkbox"
                      onChange={this.update}
                      checked={!form.captcha_disabled}
                      name="captcha_disabled"
                    />
                    <span className="slider" />
                  </label>
                </div>
              </div>
            </div>
            <div className="row">
              <div className="col-5-6">
                <h4>Email Notifications</h4>
                <p className="description">
                  You can disable the emails Formspree sends if you just want to
                  download the submissions from the dashboard.
                </p>
              </div>
              <div className="col-1-6 switch-row">
                <label className="switch">
                  <input
                    type="checkbox"
                    onChange={this.update}
                    checked={!form.disable_email}
                    name="disable_email"
                  />
                  <span className="slider" />
                </label>
              </div>
            </div>
            <div className="row">
              <div className="col-5-6">
                <h4>Submission Archive</h4>
                <p className="description">
                  You can disable the submission archive if you don't want
                  Formspree to store your submissions.
                </p>
              </div>
              <div className="col-1-6 switch-row">
                <label className="switch">
                  <input
                    type="checkbox"
                    onChange={this.update}
                    checked={!form.disable_storage}
                    name="disable_storage"
                  />
                  <span className="slider" />
                </label>
              </div>
            </div>
            <div className="row">
              <div className={this.state.deleting ? 'col-1-2' : 'col-5-6'}>
                <h4>
                  {this.state.deleting
                    ? 'Are you sure you want to delete?'
                    : 'Delete Form'}
                </h4>
                <p className="description">
                  {this.state.deleting ? (
                    <span>
                      This will delete the form on <b>{form.host}</b> targeting{' '}
                      <b>{form.email}</b> and all its submissions? This action{' '}
                      <b>cannot</b> be undone.
                    </span>
                  ) : (
                    <span>
                      Deleting the form will erase all traces of this form on
                      our databases, including all the submissions.
                    </span>
                  )}
                </p>
              </div>
              <div
                className={
                  (this.state.deleting ? 'col-1-2' : 'col-1-6') + ' switch-row'
                }
              >
                {this.state.deleting ? (
                  <>
                    <button
                      onClick={this.deleteForm}
                      className="no-uppercase destructive"
                    >
                      Sure, erase everything
                    </button>
                    <button
                      onClick={this.cancelDelete}
                      className="no-uppercase"
                      style={{marginRight: '5px'}}
                    >
                      No, don't delete!
                    </button>
                  </>
                ) : (
                  <a onClick={this.deleteForm} href="#">
                    <i className="fa fa-trash-o delete" />
                  </a>
                )}
              </div>
            </div>
          </div>
        </div>
      </>
    )
  }

  async update(e) {
    try {
      let res = await (await fetch(`/api/forms/${this.props.form.hashid}`, {
        method: 'PATCH',
        body: JSON.stringify({
          [e.currentTarget.name]: !e.currentTarget.checked
        }),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json'
        }
      })).json()

      if (res.error) {
        toastr.warning(`Failed to save settings: ${res.error}`)
        return
      }

      toastr.success('Settings saved.')
      this.props.onUpdate()
    } catch (e) {
      console.error(e)
      toastr.error('Failed to update form. See the console for more details.')
    }
  }

  cancelDelete(e) {
    e.preventDefault()
    this.setState({deleting: false})
  }

  async deleteForm(e) {
    e.preventDefault()

    if (this.props.form.counter > 0 && !this.state.deleting) {
      // double-check the user intentions to delete,
      // but only if the form has been used already.
      this.setState({deleting: true})
      return
    }

    this.setState({deleting: false})
    try {
      let res = await (await fetch(`/api/forms/${this.props.form.hashid}`, {
        method: 'DELETE',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json'
        }
      })).json()

      if (res.error) {
        toastr.warning(`Failed to delete form: ${res.error}`)
        return
      }

      toastr.success('Form successfully deleted.')
      this.props.history.push('/forms')
    } catch (e) {
      console.error(e)
      toastr.error('Failed to delete form. See the console for more details.')
    }
  }
}
