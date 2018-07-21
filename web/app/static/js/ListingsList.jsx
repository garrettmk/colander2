import React from "react";
import ObjectTable from "./ObjectTable"


export default class ListingsList extends React.Component {

    constructor (props) {
        super(props);
        this.fetchListings = this.fetchListings.bind(this);

        this.state = {
            loading: true,
            listings: []
        }
    }

    componentDidMount () {
        this.fetchListings();
    }

    fetchListings () {
        this.setState({ loading: true });

        const url = '/api/obj/listing';
        const query = { vendor_id: this.props.vendorId };
        const view = { _only: ['id', 'vendor_id', 'sku', 'title'] }

        const queryStr = encodeURIComponent(JSON.stringify(query));
        const viewStr = encodeURIComponent(JSON.stringify(view));

        fetch(`${url}?_query=${queryStr}&_view=${viewStr}`).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch listings.')
        }).then(results => {
            this.setState({
                loading: false,
                total: results.total,
                page: results.page,
                pages: results.pages,
                perPage: results.perPage,
                listings: results.items
            })
        }).catch(error => {
            alert(error);
            this.setState({ loading: false })
        })
    }

    render () {
        return <ObjectTable
                    title='Listings'
                    linkOnAttr='title'
                    linkPrefix='/listings/'
                    loading={this.state.loading}
                    total={this.state.total}
                    page={this.state.page}
                    pages={this.state.pages}
                    objects={this.state.listings}
                    fields={{
                        ID: 'id',
                        Vendor: 'vendor_id',
                        SKU: 'sku',
                        Title: 'title'
                    }}
                />

        // return ObjectTable({
        //     title: 'Listings',
        //     fields: {
        //         ID: 'id',
        //         Vendor: 'vendor_id',
        //         SKU: 'sku',
        //         Title: 'title'
        //     },
        //     linkOnAttr: 'title',
        //     linkPrefix: '/listings/',
        //     loading: this.state.loading,
        //     total: this.state.total,
        //     objects: this.state.listings,
        //     page: this.state.page,
        //     pages: this.state.pages,
        //     // onNextPage: props.onNextPage,
        //     // onPrevPage: props.onPrevPage
        // })
    }
}