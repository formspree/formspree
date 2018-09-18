/** @format */

const React = require('react')

import {ConfigContext, AccountContext} from '../Dashboard'
import {PlanView} from './Billing'

class Account extends React.Component {
  constructor(props) {
    super(props)

    this.addEmailAddress = this.addEmailAddress.bind(this)

    this.state = {}
  }

  render() {
    let {user, sub, emails, config} = this.props

    return (
      <div className="row">
        <div className="col-1-2">
          <div className="card">
            <h3>Your emails</h3>
            <p>
              You are registered with the email{' '}
              <span className="code">{user.email}</span> since{' '}
              {user.registered_on}.
            </p>
            <table className="emails">
              <tbody>
                <tr>
                  <td colSpan="2">
                    <form onSubmit={this.addEmailAddress}>
                      <input
                        name="address"
                        placeholder="Add an email to your account"
                      />
                      <button
                        type="submit"
                        style={{fontSize: '0.76em', padding: '1em 0.9em'}}
                      >
                        Verify
                      </button>
                    </form>
                  </td>
                </tr>
                {emails.pending.map(email => (
                  <tr key={email} className="waiting_confirmation">
                    <td>{email}</td>
                    <td>
                      <span
                        className="tooltip hint--right"
                        data-hint="Waiting verification. Please check your mailbox."
                      >
                        <span className="ion-pause" />
                      </span>
                    </td>
                  </tr>
                ))}
                {emails.verified.map(email => (
                  <tr key={email} className="verified">
                    <td>{email}</td>
                    <td>
                      <span
                        className="tooltip hint--right"
                        data-hint="This address is verified. You can freely control forms that post to it."
                      >
                        <span className="ion-checkmark-round" />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        <div className="col-1-2">
          <PlanView user={user} sub={sub} config={config} />
        </div>
      </div>
    )
  }

  addEmailAddress(e) {
    e.preventDefault()
  }
}

export default props => (
  <>
    <ConfigContext.Consumer>
      {config => (
        <AccountContext.Consumer>
          {({user, sub, emails}) => (
            <Account
              {...props}
              config={config}
              user={user}
              sub={sub}
              emails={emails}
            />
          )}
        </AccountContext.Consumer>
      )}
    </ConfigContext.Consumer>
  </>
)
