import React from "react";
import { Route, Link } from "react-router-dom";
import DashboardView from "./DashboardView";
import SearchView from "./SearchView";
import VendorView from "./VendorView";
import ListingView from "./ListingView";
import OrderView from "./OrderView";
import SearchBox from "./SearchBox";
import queryString from "query-string";


class App extends React.Component {

    constructor (props) {
        super(props);
    }

    render () {
        const query = queryString.parse(location.search);

        return (
            <div>
                <ul>
                    <li><Link to={'/'}>Home</Link></li>
                    <li><Link to={'/search'}>Search</Link></li>
                    <li><SearchBox input={query.query}/></li>
                </ul>
                <hr/>
                <Route exact path={'/'} component={DashboardView}/>
                <Route path={'/search'} component={SearchView}/>
                <Route path={'/vendors/:vendorId'} component={VendorView}/>
                <Route path={'/listings/:listingId'} component={ListingView}/>
                <Route path={'/orders/:orderId'} component={OrderView}/>
            </div>
        );
    }
}

export default App;