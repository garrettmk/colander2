import React from "react";
import ListingsList from "./ListingsList";
import VendorsList from "./VendorsList";


export default class SearchView extends React.Component {

    constructor(props) {
        super(props);
        this.state = {
            loading: true,
            results: {
                total: 0,
                listing: {
                    total: 0,
                    results: []
                },
                vendor: {
                    total: 0,
                    results: []
                }
            }
        };

        this.fetchResults = this.fetchResults.bind(this);
    }

    fetchResults () {
        this.setState({
            loading: true
        });

        fetch('/api/search' + this.props.location.search).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Search request failed.');
        }).then(results => {
            this.setState({
                loading: false,
                results
            })
        }).catch(error => {
            this.setState({
                loading: false,
                results: {}
            });
            alert(error);
        })
    }

    componentDidMount () {
        this.fetchResults();
    }

    componentDidUpdate (prevProps, prevState) {
        if (this.props.location.search !== prevProps.location.search)
            this.fetchResults()
    }

    render () {
        return (
            <div>
                <h2>SearchView</h2>
                <p>Location: {this.props.location.search}</p>
                <VendorsList
                    loading={this.state.loading}
                    total={this.state.results.vendor.total}
                    vendors={this.state.results.vendor.results}
                />
                <ListingsList
                    loading={this.state.loading}
                    total={this.state.results.listing.total}
                    listings={this.state.results.listing.results}
                />
            </div>
        )
    }
}
