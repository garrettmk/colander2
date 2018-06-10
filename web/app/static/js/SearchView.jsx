import React from "react";
import update from "immutability-helper";
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
                    page: 0,
                    pages: 0,
                    results: []
                },
                vendor: {
                    total: 0,
                    page: 0,
                    pages: 0,
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

    loadResultsPage (modelType, page) {
        if (page < 1 || page > this.state.results[modelType].pages)
            return;

        const query = new URLSearchParams(this.props.location.search).get('query');

        this.setState(currentState => {
            return update(currentState, {
                results: {
                    [modelType]: {
                        loading: {$set: true}
                    }
                }
            })
        });

        fetch(`/api/search?query=${query}&types=${modelType}&page=${page}`).then(response => {
            if (response.ok)
                return response.json()
            throw new Error('Could not load results.')
        }).then(results => {
            this.setState(currentState => {
                return update(currentState, {
                    results: {
                        [modelType]: {
                            loading: {$set: false},
                            page: {$set: results[modelType].page},
                            pages: {$set: results[modelType].pages},
                            results: {$set: results[modelType].results}
                        }
                    }
                })
            })
        }).catch(error => {
            this.setState(currentState => {
                return update(currentState, {
                    results: {
                        [modelType]: {
                            loading: {$set: false}
                        }
                    }
                })
            })
        })
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
                    page={this.state.results.vendor.page}
                    pages={this.state.results.vendor.pages}
                    onNextPage={() => this.loadResultsPage('vendor', this.state.results.vendor.page + 1)}
                    onPrevPage={() => this.loadResultsPage('vendor', this.state.results.vendor.page - 1)}
                />
                <ListingsList
                    loading={this.state.loading}
                    total={this.state.results.listing.total}
                    listings={this.state.results.listing.results}
                    page={this.state.results.listing.page}
                    pages={this.state.results.listing.pages}
                    onNextPage={() => this.loadResultsPage('listing', this.state.results.listing.page + 1)}
                    onPrevPage={() => this.loadResultsPage('listing', this.state.results.listing.page - 1)}
                />
            </div>
        )
    }
}
