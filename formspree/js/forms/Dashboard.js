/** @format */

const React = require('react')
const {BrowserRouter: Router, Route} = require('react-router-dom')

import FormList from './FormList'
import FormPage from './FormPage'

export default class Dashboard extends React.Component {
  render() {
    return (
      <Router>
        <>
          <Route exact path="/forms" component={FormList} />
          <Route exact path="/dashboard" component={FormList} />
          <Route path="/forms/:hashid" component={FormPage} />
        </>
      </Router>
    )
  }
}
