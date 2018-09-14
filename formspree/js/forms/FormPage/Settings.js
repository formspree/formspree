/** @format */

const toastr = window.toastr
const fetch = window.fetch
const React = require('react')

const FormDescription = require('./FormDescription')

module.exports = class FormSettings extends React.Component {
  constructor(props) {
    super(props)

    this.update = this.update.bind(this)
    this.deleteForm = this.deleteForm.bind(this)
    this.cancelDelete = this.cancelDelete.bind(this)

    this.state = {
      deleting: false,
      temporaryFormChanges: {}
    }
  }

  render() {
    let {form} = this.props
    let tmp = this.state.temporaryFormChanges

    return (
      <>
        <div className="col-1-1" id="settings">
          <FormDescription prefix="Settings for" form={form} />
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
                    checked={'disabled' in tmp ? !tmp.disabled : !form.disabled}
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
                      checked={
                        'captcha_disabled' in tmp
                          ? !tmp.captcha_disabled
                          : !form.captcha_disabled
                      }
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
                    checked={
                      'disable_email' in tmp
                        ? !tmp.disable_email
                        : !form.disable_email
                    }
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
                    checked={
                      'disable_storage' in tmp
                        ? !tmp.disable_storage
                        : !form.disable_storage
                    }
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
    let attr = e.currentTarget.name
    let val = !e.currentTarget.checked

    this.setState(state => {
      state.temporaryFormChanges[attr] = val
      return state
    })

    try {
      let resp = await fetch(`/api-int/forms/${this.props.form.hashid}`, {
        method: 'PATCH',
        body: JSON.stringify({
          [attr]: val
        }),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json'
        }
      })
      let r = await resp.json()

      if (!resp.ok || r.error) {
        toastr.warning(
          r.error
            ? `Failed to save settings: ${r.error}`
            : 'Failed to save settings.'
        )
        return
      }

      toastr.success('Settings saved.')
      this.props.onUpdate().then(() => {
        this.setState({temporaryFormChanges: {}})
      })
    } catch (e) {
      console.error(e)
      toastr.error('Failed to update form. See the console for more details.')
      this.setState({temporaryFormChanges: {}})
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
      let resp = await fetch(`/api-int/forms/${this.props.form.hashid}`, {
        method: 'DELETE',
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json'
        }
      })
      let r = await resp.json()

      if (resp.error || r.error) {
        toastr.warning(
          r.error
            ? `failed to delete form: ${r.error}`
            : 'failed to delete form.'
        )
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
