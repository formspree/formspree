/** @format */

const toastr = window.toastr
const fetch = window.fetch
const React = require('react')
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

export const ConfigContext = React.createContext()
export const AccountContext = React.createContext()

export default class Dashboard extends React.Component {
  constructor() {
    super()

    this.state = {
      config: null,
      account: null
    }
  }

  componentDidMount() {
    Promise.all([
      (async () => {
        try {
          let resp = await fetch('/api-int/config', {
            headers: {Accept: 'application/json'}
          })

          this.setState({
            config: await resp.json()
          })
        } catch (e) {
          console.error(e)
          this.setState({error: e.message})
          toastr.error(
            'Failed to fetch config. See the console for more details.'
          )
        }
      })(),
      (async () => {
        try {
          let resp = await fetch('/api-int/account', {
            credentials: 'same-origin',
            headers: {Accept: 'application/json'}
          })
          let r = await resp.json()

          if (!resp.ok || r.error) {
            throw new Error(r.error || '')
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
        } catch (e) {
          console.error(e)
          this.setState({error: e.message})
          toastr.error(
            'Failed to fetch your account data. See the console for more details.'
          )
        }
      })()
    ])
  }

  render() {
    if (!this.state.config || !this.state.account) {
      return <p>loading...</p>
    }

    return (
      <Router>
        <ConfigContext.Provider value={this.state.config}>
          <AccountContext.Provider value={this.state.account}>
            <Portal to=".menu .item:nth-child(2)">
              <Link to="/forms">Your forms</Link>
            </Portal>
            <Portal to=".menu .item:nth-child(3)">
              <Link to="/account">Your account</Link>
            </Portal>
            <Switch>
              <Redirect from="/dashboard" to="/forms" />
              <Route exact path="/account" component={Account} />
              <Route exact path="/account/billing" component={Billing} />
              <Route exact path="/forms" component={FormList} />
              <Route path="/forms/:hashid" component={FormPage} />
            </Switch>
          </AccountContext.Provider>
        </ConfigContext.Provider>
      </Router>
    )
  }
}
