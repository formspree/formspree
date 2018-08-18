/** @format */

const React = require('react')
const render = require('react-dom').render
const {BrowserRouter: Router, Route} = require('react-router-dom')

const FormList = require('./FormList')
const FormPage = require('./FormPage')

class Dashboard extends React.Component {
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

document.querySelector('.menu .item:nth-child(2)').innerHTML = ''
render(<Dashboard />, document.querySelector('.container.block'))
