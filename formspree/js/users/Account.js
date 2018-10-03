/** @format */

const toastr = window.toastr
const fetch = window.fetch
const React = require('react')

import {AccountContext} from '../Dashboard'
import {PlanView} from './Billing'

class Account extends React.Component {
  constructor(props) {
    super(props)

    this.addEmailAddress = this.addEmailAddress.bind(this)

    this.state = {
      newPending: []
    }
  }

  render() {
    let {user, sub, emails} = this.props
    let {newPending} = this.state

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
                        key={newPending.length}
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
                {newPending.concat(emails.pending).map(email => (
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
          <PlanView user={user} sub={sub} />
        </div>
      </div>
    )
  }

  async addEmailAddress(e) {
    e.preventDefault()

    let address = e.target.address.value

    try {
      let resp = await fetch(`/api-int/account/add-email`, {
        method: 'POST',
        body: JSON.stringify({address}),
        credentials: 'same-origin',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json'
        }
      })

      switch (resp.status) {
        case 200:
          toastr.info(`${address} is already registered for your account.`)
          break
        case 202:
          toastr.success(
            `We've sent a message with a verification link to ${address}`
          )
          this.setState(st => {
            st.newPending.unshift(address)
            return st
          })
          break
        default:
          let r = await resp.json()
          toastr.error(r.error)
          break
      }
    } catch (e) {
      console.error(e)
      toastr.error(
        'Failed add email to your account, see the console for more details.'
      )
    }
  }
}

export default props => (
  <>
    <AccountContext.Consumer>
      {({user, sub, emails}) => (
        <Account {...props} user={user} sub={sub} emails={emails} />
      )}
    </AccountContext.Consumer>
  </>
)
