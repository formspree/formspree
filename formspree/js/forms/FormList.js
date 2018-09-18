/** @format */

const toastr = window.toastr
const fetch = window.fetch
const React = require('react')
const cs = require('class-set')
const {Link} = require('react-router-dom')

const CreateForm = require('./CreateForm')
const Portal = require('../Portal')

module.exports = class FormList extends React.Component {
  constructor(props) {
    super(props)

    this.state = {
      loading: true,
      user: {},
      enabled_forms: [],
      disabled_forms: [],
      error: null
    }
  }

  async componentDidMount() {
    try {
      let resp = await fetch('/api-int/forms', {
        credentials: 'same-origin',
        headers: {Accept: 'application/json'}
      })
      let r = await resp.json()

      if (!resp.ok || r.error) {
        throw new Error(r.error || '')
      }

      this.setState({
        user: r.user,
        enabled_forms: r.forms.filter(f => !f.disabled),
        disabled_forms: r.forms.filter(f => f.disabled),
        loading: false
      })
    } catch (e) {
      console.error(e)
      this.setState({error: e.message})
      toastr.error(
        'Failed to fetch your forms. See the console for more details.'
      )
    }
  }

  render() {
    if (this.state.loading) {
      return (
        <div className="col-1-1">
          <p>loading...</p>
        </div>
      )
    }

    if (this.state.error) {
      return (
        <div className="col-1-1">
          <p>
            An error has ocurred while we were trying to fetch your forms,
            please try again or contact us at support@formspree.io.
          </p>
        </div>
      )
    }

    return (
      <>
        <Portal to=".menu .item:nth-child(2)">
          <Link to="/forms">Your forms</Link>
        </Portal>
        <Portal to="#header .center">
          <h1>Your Forms</h1>
        </Portal>
        <div className="col-1-1">
          <h4>Active Forms</h4>
          {this.state.enabled_forms.length ? (
            <table className="forms responsive">
              <tbody>
                {this.state.enabled_forms.map(form => (
                  <FormItem key={form.hashid} {...form} />
                ))}
              </tbody>
            </table>
          ) : (
            <p>
              No active forms found. Forms can be enabled by clicking the unlock
              icon below.
            </p>
          )}

          {this.state.disabled_forms.length ? (
            <>
              <h4>Disabled Forms</h4>
              <table className="forms responsive">
                <tbody>
                  {this.state.disabled_forms.map(form => (
                    <FormItem key={form.hashid} {...form} />
                  ))}
                </tbody>
              </table>
            </>
          ) : null}

          {this.state.enabled_forms.length === 0 &&
          this.state.disabled_forms.length === 0 &&
          this.state.user.features.dashboard ? (
            <h6 className="light">
              You don't have any forms associated with this account, maybe you
              should <a href="/account">verify your email</a>.
            </h6>
          ) : null}
        </div>

        <CreateForm user={this.state.user} {...this.props} />
      </>
    )
  }
}

class FormItem extends React.Component {
  render() {
    let form = this.props

    return (
      <tr
        className={cs({
          new: form.counter === 0,
          verified: form.confirmed,
          waiting_confirmation: form.confirm_sent
        })}
      >
        <td data-label="Status">
          <Link to={`/forms/${form.hashid}/settings`} className="no-underline">
            {form.host ? (
              form.confirmed ? (
                <span
                  className="tooltip hint--right"
                  data-hint="Form confirmed"
                >
                  <span className="ion-checkmark-round" />
                </span>
              ) : form.confirm_sent ? (
                <span
                  className="tooltip hint--right"
                  data-hint="Waiting confirmation"
                >
                  <span className="ion-pause" />
                </span>
              ) : null
            ) : (
              <span
                className="tooltip hint--right"
                data-hint="New form. Place the code generated here in some page and submit it!"
              >
                <span className="ion-help" />
              </span>
            )}
          </Link>
        </td>
        <td data-label="URL">
          {form.host ? (
            <div>
              {form.host}
              {form.sitewide ? (
                <span
                  className="highlight tooltip hint--top"
                  data-hint="This form works for all paths under {{ form.host }}/"
                >
                  / *
                </span>
              ) : null}
            </div>
          ) : (
            'Waiting for a submission'
          )}
        </td>
        <td className="target-email" data-label="Target email address">
          {form.email}
        </td>
        <td className="n-submissions" data-label="Submissions counter">
          {form.counter === 0 ? (
            <Link
              to={`/forms/${form.hashid}/integration`}
              className="no-underline"
            >
              <span className="never">never submitted</span>
            </Link>
          ) : (
            <Link
              to={`/forms/${form.hashid}/submissions`}
              className="no-underline"
            >
              {form.counter} submissions
            </Link>
          )}
        </td>
        <td>
          {form.features.whitelabel && (
            <Link
              to={`/forms/${form.hashid}/whitelabel`}
              className="no-underline"
            >
              {form.template ? (
                <span
                  className="tooltip hint--top"
                  data-hint="Uses a custom email template."
                >
                  <span className="ion-document-text" />
                </span>
              ) : (
                <span
                  className="tooltip hint--top"
                  data-hint="Doesn't use a custom email template."
                >
                  <span className="ion-document" />
                </span>
              )}
            </Link>
          )}
        </td>
        <td>
          <Link to={`/forms/${form.hashid}/settings`} className="no-underline">
            <span className="ion-gear-b" />
          </Link>
        </td>
      </tr>
    )
  }
}
