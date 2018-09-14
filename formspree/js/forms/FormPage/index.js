/** @format */

const toastr = window.toastr
const fetch = window.fetch
const React = require('react')
const {Route, Link, NavLink, Redirect} = require('react-router-dom')

const Portal = require('../../Portal')
const Integration = require('./Integration')
const Submissions = require('./Submissions')
const Settings = require('./Settings')
const Whitelabel = require('./Whitelabel')

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
          <h1>Form Details</h1>
        </Portal>
        <Route
          exact
          path={`/forms/${hashid}`}
          render={() => <Redirect to={`/forms/${hashid}/submissions`} />}
        />
        {this.state.form && (
          <>
            <h4 className="tabs">
              <NavLink
                to={`/forms/${hashid}/integration`}
                activeStyle={{color: 'inherit', cursor: 'normal'}}
              >
                Integration
              </NavLink>
              <NavLink
                to={`/forms/${hashid}/submissions`}
                activeStyle={{color: 'inherit', cursor: 'normal'}}
              >
                Submissions
              </NavLink>
              <NavLink
                to={`/forms/${hashid}/settings`}
                activeStyle={{color: 'inherit', cursor: 'normal'}}
              >
                Settings
              </NavLink>
              {this.state.form.features.whitelabel && (
                <NavLink
                  to={`/forms/${hashid}/whitelabel`}
                  activeStyle={{color: 'inherit', cursor: 'normal'}}
                >
                  Whitelabel
                </NavLink>
              )}
            </h4>
            <Route
              path="/forms/:hashid/integration"
              render={() => (
                <Integration form={this.state.form} onUpdate={this.fetchForm} />
              )}
            />
            <Route
              path="/forms/:hashid/submissions"
              render={() => (
                <Submissions form={this.state.form} onUpdate={this.fetchForm} />
              )}
            />
            <Route
              path="/forms/:hashid/settings"
              render={() => (
                <Settings
                  form={this.state.form}
                  history={this.props.history}
                  onUpdate={this.fetchForm}
                />
              )}
            />
            <Route
              path="/forms/:hashid/whitelabel"
              render={() => (
                <Whitelabel form={this.state.form} onUpdate={this.fetchForm} />
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
      let resp = await fetch(`/api-int/forms/${hashid}`, {
        credentials: 'same-origin',
        headers: {Accept: 'application/json'}
      })
      let r = await resp.json()

      if (!resp.ok || r.error) {
        toastr.warning(
          r.error ? `Error fetching form: ${r.error}` : 'Error fetching form.'
        )
        return
      }

      this.setState({form: r})
    } catch (e) {
      console.error(e)
      toastr.error(`Failed to fetch form, see the console for more details.`)
    }
  }
}
