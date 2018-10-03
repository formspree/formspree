/** @format */

const toastr = window.toastr
const fetch = window.fetch
const React = require('react')
const {StripeProvider} = require('react-stripe-elements')
const {
  BrowserRouter: Router,
  Route,
  Redirect,
  Switch,
  Link
} = require('react-router-dom')

import Portal from './Portal'
import FormList from './forms/FormList'
import FormPage from './forms/FormPage'
import Account from './users/Account'
import Billing from './users/Billing'
import Plans from './users/Plans'

export const AccountContext = React.createContext()

export default class Dashboard extends React.Component {
  constructor() {
    super()

    this.state = {
      account: null
    }
  }

  componentDidMount() {
    Promise.all([
      (async () => {
        if (location.pathname === '/plans') {
          this.setState({account: {}})
          return
        }

        var r
        try {
          let resp = await fetch('/api-int/account', {
            credentials: 'same-origin',
            headers: {Accept: 'application/json'}
          })
          r = await resp.json()

          if (!resp.ok || r.error) {
            throw new Error(r.error || '')
          }
        } catch (e) {
          console.error(e)
          this.setState({error: e.message})
          toastr.error(
            'Failed to fetch your account data. See the console for more details.'
          )
          return
        }

        this.setState({
          account: {
            user: r.user,
            emails: r.emails,
            sub: r.sub,
            cards: r.cards,
            invoices: r.invoices
          }
        })
      })()
    ])
  }

  render() {
    if (!this.state.account) {
      return <p>loading...</p>
    }

    return (
      <Router>
        <StripeProvider apiKey={window.formspree.STRIPE_PUBLISHABLE_KEY}>
          <AccountContext.Provider value={this.state.account}>
            <Portal to="#forms-menu-item">
              <Link to="/forms">Your forms</Link>
            </Portal>
            <Portal to="#account-menu-item">
              <Link to="/account">Your account</Link>
            </Portal>
            <Switch>
              <Redirect from="/dashboard" to="/forms" />
              <Route exact path="/plans" component={Plans} />
              <Route exact path="/account" component={Account} />
              <Route exact path="/account/billing" component={Billing} />
              <Route exact path="/forms" component={FormList} />
              <Route path="/forms/:hashid" component={FormPage} />
            </Switch>
          </AccountContext.Provider>
        </StripeProvider>
      </Router>
    )
  }
}
