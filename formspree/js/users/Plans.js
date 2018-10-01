/** @format */

const toastr = window.toastr
const fetch = window.fetch
const React = require('react')

import {ConfigContext, AccountContext} from '../Dashboard'
import Modal from '../Modal'

const STEP_DOWNGRADE = -1
const STEP_NOTHING = 0
const STEP_REGISTER = 1
const STEP_PERSONAL = 2
const STEP_PAYMENT = 3

class Plans extends React.Component {
  constructor(props) {
    super(props)

    this.select = this.select.bind(this)
    this.prev = this.prev.bind(this)
    this.next = this.next.bind(this)
    this.closeModal = this.closeModal.bind(this)

    this.state = {
      step: STEP_NOTHING,
      modal_opened: false,
      data: {
        product: null, // this is "Gold" or "Platinum", without specifying the plan id
        email: this.props.user && this.props.user.email,
        password: null,
        passwordcheck: null,
        name: null,
        address: null,
        country: null,
        zip: null,
        plan: null
      }
    }
  }

  render() {
    console.log(this.props)
    let {config, user} = this.props
    let {data, step, modal_opened} = this.state

    return (
      <div className="container">
        <div className="row">
          <div className="col-1-3">
            <h1>Free</h1>
            <ul>
              <li>Free is bad</li>
              <li>Free has no features</li>
            </ul>
            <button
              onClick={this.select('Free')}
              disabled={!user || user.plan === 'Free'}
            >
              Select
            </button>
          </div>
          <div className="col-1-3">
            <h1>Gold</h1>
            <ul>
              <li>Gold is good</li>
              <li>Gold has features</li>
            </ul>
            <button
              onClick={this.select('Gold')}
              disabled={user && user.plan === 'Gold'}
            >
              Select
            </button>
          </div>
          <div className="col-1-3">
            <h1>Platinum</h1>
            <ul>
              <li>Platinum is great</li>
              <li>But diamonds are better</li>
            </ul>
            <button
              onClick={this.select('Platinum')}
              disabled={user && user.plan === 'Platinum'}
            >
              Select
            </button>
          </div>
        </div>
        {user && (
          <Modal
            title="Downgrade"
            opened={modal_opened && step === STEP_DOWNGRADE}
            onClose={this.closeModal}
          >
            <div>
              <div>
                <h1>Do you really want to cancel your {user.plan} plan?</h1>
                <button onClick={this.next}>Yes</button>
                <button onClick={this.closeModal}>No, keep my plan!</button>
              </div>
            </div>
          </Modal>
        )}
        <Modal
          title={`Formspree ${data.plan}`}
          opened={modal_opened && step === STEP_REGISTER}
          onClose={this.closeModal}
        >
          <div>
            <div>
              <form onSubmit={this.next}>
                <label>
                  Email:{' '}
                  <input
                    type="email"
                    autoComplete="email"
                    required
                    onChange={this.setData('email')}
                  />
                </label>
                <label>
                  Password:{' '}
                  <input
                    type="password"
                    required
                    onChange={this.setData('password')}
                  />
                </label>
                <label>
                  Password (again):{' '}
                  <input
                    type="password"
                    required
                    onChange={this.setData('passwordcheck')}
                  />
                </label>
              </form>
            </div>
            <div className="container right">
              <button onClick={this.next}>Next</button>
            </div>
          </div>
        </Modal>
        <Modal
          title={`Formspree ${data.plan}`}
          opened={modal_opened && step === STEP_PERSONAL}
          onClose={this.closeModal}
        >
          <div>
            {!user && (
              <div className="container left">
                <button onClick={this.prev}>Back</button>
              </div>
            )}
            <div>
              <form onSubmit={this.next}>
                <label>
                  Name:{' '}
                  <input
                    autoComplete="name"
                    required
                    onChange={this.setData('name')}
                  />
                </label>
                <label>
                  Address:{' '}
                  <input
                    autoComplete="street-address"
                    required
                    onChange={this.setData('address')}
                  />
                </label>
                <label>
                  Country:{' '}
                  <input
                    autoComplete="country"
                    required
                    onChange={this.setData('country')}
                  />
                </label>
                <label>
                  Zip:{' '}
                  <input
                    autoComplete="postal-code"
                    required
                    onChange={this.setData('zip')}
                  />
                </label>
              </form>
            </div>
            <div className="container right">
              <button onClick={this.next}>Next</button>
            </div>
          </div>
        </Modal>
        <Modal
          title={`Formspree ${data.plan}`}
          opened={modal_opened && step === STEP_PAYMENT}
          onClose={this.closeModal}
        >
          <div>
            <div className="container left">
              <button onClick={this.prev}>Back</button>
            </div>
            <div />
            <div className="container">
              <button className="row" onClick={this.next}>
                Purchase
              </button>
            </div>
          </div>
        </Modal>
      </div>
    )
  }

  closeModal(e) {
    e.preventDefault()

    this.setState({modal_opened: false})
  }

  select(planName) {
    return e => {
      e.preventDefault()

      this.setState(state => {
        state.modal_opened = true

        state.data.plan = planName

        if (planName === 'Free') {
          state.step = STEP_DOWNGRADE
        } else if (this.props.user) {
          state.step = STEP_PERSONAL
        } else {
          state.step = STEP_REGISTER
        }

        return state
      })
    }
  }

  next(e) {
    e.preventDefault()
    let {data, step} = this.state

    switch (step) {
      case STEP_DOWNGRADE:
        // downgrade user now
        break
      case STEP_REGISTER:
        if (data.email && data.password) {
          // alert required fields
          break
        }
        if (data.password !== data.passwordcheck) {
          // alert passwords don't match
          break
        }

        this.setState({step: STEP_PERSONAL})
        break
      case STEP_PERSONAL:
        // do some address and country validatin here?
        this.setState({step: STEP_PAYMENT})
        break
      case STEP_PAYMENT:
        // do the stripe stuff and subscribe user
        break
    }
  }

  prev(e) {
    e.preventDefault()
    this.setState(state => {
      state.step--
      return state
    })
  }

  setData(key) {
    return e => {
      e.preventDefault()
      let value = e.target.value

      this.setState(state => {
        state.data[key] = value
        return state
      })
    }
  }
}

export default props => (
  <>
    <ConfigContext.Consumer>
      {config => (
        <AccountContext.Consumer>
          {({user}) => <Plans {...props} config={config} user={user} />}
        </AccountContext.Consumer>
      )}
    </ConfigContext.Consumer>
  </>
)
