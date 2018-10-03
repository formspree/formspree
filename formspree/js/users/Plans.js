/** @format */

const toastr = window.toastr
const fetch = window.fetch
const formspree = window.formspree
const React = require('react')
const {CardElement, Elements, injectStripe} = require('react-stripe-elements')

import {AccountContext} from '../Dashboard'
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
    this.setData = this.setData.bind(this)
    this.prev = this.prev.bind(this)
    this.next = this.next.bind(this)
    this.closeModal = this.closeModal.bind(this)

    this.state = {
      step: STEP_NOTHING,
      modalOpened: false,
      data: {
        product: null, // this is "Gold" or "Platinum", without specifying the plan id
        plan: null, // this is the plan
        email: '',
        password: '',
        passwordcheck: '',
        name: '',
        address: '',
        country: 'US',
        zip: ''
      }
    }
  }

  render() {
    let {user} = this.props
    let {data, step, modalOpened} = this.state

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
              disabled={!user || user.product === 'Free'}
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
              disabled={user && user.product === 'Gold'}
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
              disabled={user && user.product === 'Platinum'}
            >
              Select
            </button>
          </div>
        </div>
        {user && (
          <Modal
            title="Downgrade"
            opened={modalOpened && step === STEP_DOWNGRADE}
            onClose={this.closeModal}
          >
            <div>
              <div>
                <h1>Do you really want to cancel your {user.product} plan?</h1>
                <button onClick={this.next}>Yes</button>
                <button onClick={this.closeModal}>No, keep my plan!</button>
              </div>
            </div>
          </Modal>
        )}
        <Modal
          title={`Formspree ${data.product}`}
          opened={modalOpened && step === STEP_REGISTER}
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
                    value={data.email}
                    onChange={this.setData('email')}
                  />
                </label>
                <label>
                  Password:{' '}
                  <input
                    type="password"
                    required
                    value={data.password}
                    onChange={this.setData('password')}
                  />
                </label>
                <label>
                  Password (again):{' '}
                  <input
                    type="password"
                    required
                    value={data.passwordcheck}
                    onChange={this.setData('passwordcheck')}
                  />
                </label>
                <div className="container right">
                  <button>Next</button>
                </div>
              </form>
            </div>
          </div>
        </Modal>
        <Modal
          title={`Formspree ${data.product}`}
          opened={modalOpened && step === STEP_PERSONAL}
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
                    value={data.name}
                    onChange={this.setData('name')}
                  />
                </label>
                <label>
                  Address:{' '}
                  <input
                    autoComplete="street-address"
                    required
                    value={data.address}
                    onChange={this.setData('address')}
                  />
                </label>
                <div className="row">
                  <label className="row-1-2">
                    Country:{' '}
                    {data.country && (
                      <img
                        src={`/static/img/countries/${data.country.toLowerCase()}.png`}
                      />
                    )}
                    <select required onChange={this.setData('country')}>
                      {formspree.countries.map(c => (
                        <option value={c} key={c} selected={c === data.country}>
                          {c}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label className="row-1-2">
                    Zip:{' '}
                    <input
                      autoComplete="postal-code"
                      required
                      value={data.zip}
                      onChange={this.setData('zip')}
                    />
                  </label>
                </div>
                <div className="container right">
                  <button>Next</button>
                </div>
              </form>
            </div>
          </div>
        </Modal>
        <Modal
          title={`Formspree ${data.product}`}
          opened={modalOpened && step === STEP_PAYMENT}
          onClose={this.closeModal}
        >
          <Elements>
            <PaymentForm
              data={this.state.data}
              setData={this.setData}
              prev={this.prev}
              next={this.next}
            />
          </Elements>
        </Modal>
      </div>
    )
  }

  closeModal(e) {
    e.preventDefault()

    this.setState({modalOpened: false})
  }

  select(productName) {
    return e => {
      e.preventDefault()

      this.setState(state => {
        state.modalOpened = true

        state.data.product = productName

        if (productName === 'Free') {
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

  async next(e) {
    e.preventDefault()
    let {data, step} = this.state

    var valid = true
    function check(fieldName) {
      if (!data[fieldName]) {
        toastr.warning(`Missing field "${fieldName}".`)
        valid = false
      }
    }

    switch (step) {
      case STEP_DOWNGRADE:
        // downgrade user now
        var r
        try {
          let resp = await fetch('/cancel', {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
              Accept: 'application/json',
              'Content-Type': 'application/json'
            }
          })
          r = await resp.json()

          if (!resp.ok || r.error) {
            toastr.warning(
              r.error
                ? `Failed to cancel your subscription: ${r.error}`
                : 'Failed to cancel youa subscription.'
            )
            return
          }
        } catch (e) {
          console.error(e)
          toastr.error(
            'Unexpected error when cancelling the subscription, see the console for more details.'
          )
        }

        toastr.success('Subscription canceled!')
        setTimeout(() => {
          location.href = '/'
        }, 4000)
        break
      case STEP_REGISTER:
        ;['email', 'password'].forEach(check)

        if (data.password !== data.passwordcheck) {
          toastr.warning(`Passwords don't match.`)
          valid = false
        }

        if (valid) {
          this.setState({step: this.state.step + 1})
        }
        break
      case STEP_PERSONAL:
        ;['name', 'address', 'country', 'zip'].forEach(check)

        if (valid) {
          this.setState({step: this.state.step + 1})
        }
        break
      case STEP_PAYMENT:
        // at this point we should have a stripe token already
        // so we proceed to register/upgrade
        try {
          let resp = await fetch('/buy', {
            method: 'POST',
            body: JSON.stringify(data),
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
                ? `Failed to create a subscription: ${r.error}`
                : 'Failed to create a subscription.'
            )
            return
          }
        } catch (e) {
          console.error(e)
          toastr.error(
            'Unexpected error when creating the subscription, see the console for more details.'
          )
        }

        toastr.success('Subscription created!')
        setTimeout(() => {
          location.href = '/account'
        }, 4000)
        break
    }
  }

  prev(e) {
    e.preventDefault()
    this.setState({step: this.state.step - 1})
  }

  setData(key) {
    return e => {
      let value = e.target.value

      this.setState(state => {
        state.data[key] = value
        return state
      })
    }
  }
}

const PaymentForm = injectStripe(
  class extends React.Component {
    constructor(props) {
      super(props)

      this.completeCheckout = this.completeCheckout.bind(this)
    }

    render() {
      let {data, setData, prev} = this.props
      let {monthly: m, yearly: y} = formspree.plans[data.product]

      return (
        <div>
          <div className="container left">
            <button onClick={prev}>Back</button>
          </div>
          <div className="container">
            <div>
              <h1>Payment</h1>
              <hr />
              <form onSubmit={this.completeCheckout}>
                <div>
                  <label>
                    <input
                      type="checkbox"
                      checked={y.id === data.plan}
                      onChange={setData('plan')}
                      value={y.id}
                    />{' '}
                    Yearly Billing ${(y.price / 12).toFixed(0)}
                    /mo ($
                    {y.price} total, ${(m.price * 12 - y.price).toFixed(0)}{' '}
                    discount){' '}
                  </label>
                </div>
                <div>
                  <label>
                    <input
                      type="checkbox"
                      checked={m.id === data.plan}
                      onChange={setData('plan')}
                      value={m.id}
                    />{' '}
                    Monthly Billing ${m.price}
                    /mo
                  </label>
                </div>
                <div>
                  <CardElement hidePostalCode />
                </div>
                <button className="row">Purchase</button>
              </form>
            </div>
          </div>
        </div>
      )
    }

    async completeCheckout(e) {
      e.preventDefault()

      let {data} = this.props
      let {token, error} = await this.props.stripe.createToken({
        name: data.name,
        address_line1: data.address,
        address_country: data.country,
        address_zip: data.zip
      })

      if (error) {
        toastr.warning(error.message)
        return
      }

      this.props.setData('token')({target: {value: token.id}})
      this.props.next()
    }
  }
)

export default props => (
  <>
    <AccountContext.Consumer>
      {({user}) => <Plans {...props} user={user} />}
    </AccountContext.Consumer>
  </>
)
