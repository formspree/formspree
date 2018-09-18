/** @format */

const React = require('react')
const toastr = window.toastr
const fetch = window.fetch

const {Link} = require('react-router-dom')

import {ConfigContext, AccountContext} from '../Dashboard'

class Billing extends React.Component {
  constructor(props) {
    super(props)

    this.state = {}
  }

  render() {
    let {config, user, sub, cards, invoices} = this.props

    return (
      <>
        <div className="row">
          <div className="col-1-2" />
          <div className="col-1-2">
            <h3>Wallet</h3>
            {sub &&
              (cards.length ? (
                <table id="card-list">
                  <tbody>
                    {cards.map(card => (
                      <>
                        <tr key={card.last4 + '1'}>
                          <td>
                            <div className="arrow">
                              <i
                                className="fa fa-chevron-right"
                                aria-hidden="true"
                              />
                            </div>
                          </td>
                          <td>
                            <i
                              className="fa fa-{ card.css_name }"
                              aria-hidden="true"
                            />
                          </td>
                          <td>
                            ••••
                            {card.last4}
                          </td>
                          <td>
                            {card.exp_month}/{card.exp_year}
                          </td>
                        </tr>
                        <tr key={card.last4 + '2'}>
                          <td colspan="4">
                            <div
                              className="actions"
                              style="float:right;width:50%;padding-left:20%;"
                            >
                              {card.default ? (
                                <p>
                                  <button
                                    style="color:white;background:#359173;border:none;"
                                    className="disabled"
                                    disabled
                                  >
                                    Default
                                  </button>
                                </p>
                              ) : (
                                <form
                                  action="{ url_for('change-default-card', cardid=card.id) }"
                                  method="POST"
                                >
                                  <button
                                    type="submit"
                                    style="margin-bottom: 18px;"
                                  >
                                    Make Default
                                  </button>
                                </form>
                              )}
                              <form
                                action="{ url_for('delete-card', cardid=card.id) }"
                                method="POST"
                              >
                                <button type="submit">Delete</button>
                              </form>
                            </div>
                            <div className="row">
                              <p>
                                Number: ••••
                                {card.last4}
                              </p>
                              <p>
                                Type: {card.brand} {card.funding} card
                              </p>
                              <p>
                                Origin: {card.country}{' '}
                                <img
                                  src={`/static/img/countries/${card.country.toLowerCase()}`}
                                  width="25"
                                />
                              </p>
                              <p>
                                CVC Check:{' '}
                                {card.cvc_check === 'pass' ? (
                                  <>
                                    Passed
                                    <i
                                      className="fa fa-check-circle-o"
                                      aria-hidden="true"
                                    />
                                  </>
                                ) : card.cvc_check === 'fail' ? (
                                  <>
                                    Failed
                                    <i
                                      className="fa fa-times-circle-o"
                                      aria-hidden="true"
                                    />
                                  </>
                                ) : (
                                  <>
                                    Unknown
                                    <i
                                      className="fa fa-question-circle"
                                      aria-hidden="true"
                                    />
                                  </>
                                )}
                              </p>
                            </div>
                          </td>
                        </tr>
                      </>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p>
                  We couldn't find any active cards in your wallet. Please make
                  sure to add a card by {sub.current_period_end} or your
                  subscription won't renew.
                </p>
              ))}

            <div className="create-form">
              <a href="#add-card" className="button">
                Add Card
              </a>
              <div className="modal narrow" id="add-card" aria-hidden="true">
                <div className="container">
                  <div className="x">
                    <h4>Add Card</h4>
                    <a href="#">&times;</a>
                  </div>
                  <form
                    method="POST"
                    action="{ url_for('add-card') }"
                    id="payment-form"
                  >
                    <div id="card-element" className="field" />
                    <div className="col-1-1">
                      <input
                        type="submit"
                        className="submit card"
                        value="Add Card"
                      />
                    </div>
                  </form>
                  <div className="col-1-1 small">
                    <p>
                      Secured with{' '}
                      <i className="fa fa-cc-stripe" aria-hidden="true" />.{' '}
                      {config.SERVICE_NAME} never sees your card number.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div className="row">
          <div className="col-1-1">
            <h3>Invoices</h3>
            <div className="card">
              <table id="invoices">
                <colgroup>
                  <col width="20%" />
                  <col width="35%" />
                  <col width="10%" />
                  <col width="10%" />
                  <col width="25%" />
                </colgroup>
                <tbody>
                  {invoices.map(
                    invoice =>
                      invoice.attempted ? (
                        <tr key={invoice.id}>
                          <td>{invoice.date}</td>
                          <td>{invoice.id}</td>
                          <td>${invoice.total / 100}</td>
                          <td>{invoice.paid ? 'Paid' : 'Unpaid'}</td>
                          <td>
                            <a
                              href={`/account/billing/invoice/${invoice.id.slice(
                                3
                              )}`}
                              className="button"
                              target="_blank"
                            >
                              View Details
                            </a>
                          </td>
                        </tr>
                      ) : null
                  )}
                </tbody>
              </table>
              <div className="create-form">
                <a href="#edit-billing" className="button">
                  Edit Invoice Address
                </a>
                <div
                  className="modal narrow"
                  id="edit-billing"
                  aria-hidden="true"
                >
                  <div className="container">
                    <div className="x">
                      <h4>Edit Invoice Address</h4>
                      <a href="#">&times;</a>
                    </div>
                    <form
                      method="POST"
                      action="{ url_for('update-invoice-address') }"
                    >
                      <textarea rows="4" name="invoice-address">
                        {user.invoice_address ? user.invoice_address : null}
                      </textarea>
                      <div className="col-1-1">
                        <input
                          type="submit"
                          className="submit card"
                          value="Update Invoice Address"
                        />
                      </div>
                    </form>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </>
    )
  }
}

export const PlanView = ({user, sub, config}) => (
  <div className="card">
    <h3>Plan</h3>
    {user.features.dashboard ? (
      <>
        <p>
          You are a {config.SERVICE_NAME} {user.plan} user.
        </p>

        {sub &&
          (sub.cancel_at_period_end ? (
            <>
              <p>
                You've cancelled your subscription and it is ending on{' '}
                {sub.current_period_end}.
              </p>
              <form action="/account/resubscribe" method="POST">
                <button type="submit">Resubscribe</button>
              </form>
            </>
          ) : (
            <p>
              Your subscription will automatically renew on{' '}
              {sub.current_period_end}.
            </p>
          ))}
        <div className="pad-top">
          <Link className="button" to="/account/billing">
            Manage Billing
          </Link>
        </div>
      </>
    ) : (
      <>
        When you upgrade you will get
        <ol style={{textAlign: 'left'}}>
          <li>Unlimited submissions</li>
          <li>Access to submission archives</li>
          <li>
            Ability to hide your email from your page's HTML and replace it with
            a random-like URL
          </li>
          <li>Ability to submit AJAX forms</li>
          <li>Ability to create forms linked to other email accounts</li>
        </ol>
        <h6 className="light">
          You are using a free account and should upgrade.
        </h6>
        <form method="post" action="/account/upgrade">
          <button
            id="stripe-upgrade"
            data-key={config.STRIPE_PUBLISHABLE_KEY}
            data-image="/static/img/logo.png"
            data-name={config.SERVICE_NAME}
            data-description={`${config.SERVICE_NAME} ${
              config.UPGRADED_PLAN_NAME
            } monthly subscription`}
            data-amount="999"
            data-email={user.email}
            data-allowRememberMe="false"
            data-zip-code="true"
            data-locale="true"
            data-billing-address="true"
            data-panel-label="Subscribe"
          >
            Upgrade for 9.99 / month
          </button>
        </form>
      </>
    )}
  </div>
)

export default props => (
  <>
    <ConfigContext.Consumer>
      {config => (
        <AccountContext.Consumer>
          {({user, sub, cards, invoices}) => (
            <Billing
              {...props}
              config={config}
              user={user}
              sub={sub}
              cards={cards}
              invoices={invoices}
            />
          )}
        </AccountContext.Consumer>
      )}
    </ConfigContext.Consumer>
  </>
)
