import React from "react";
import VendorDetails from "./VendorDetails";
import ListingDetails from "./ListingDetails";
import { fetchVendor, fetchVendorNames, fetchListing } from "./colander";
import ExtraDetails from "./ExtraDetails";
import InventoryList from "./InventoryList";


export default class ListingView extends React.Component {

    constructor (props) {
        super(props);

        this.state = {
            loading: true,
            listing: {},
            vendor: {},
            inventories: {}
        };
    }

    componentDidMount () {
        fetchListing(this.props.match.params.listingId).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch listing.')
        }).then(results => {
            this.setState({
                listing: results.items[0]
            });

            fetchVendor(this.state.listing.vendor_id, { getAttrs: ['abbreviated'] }).then(response => {
                if (response.ok)
                    return response.json();
                throw new Error('Could not load vendor info.')
            }).then(results => {
                this.setState({
                    loading: false,
                    vendor: results.items[0]
                })
            });

            fetch(`/api/obj/inventory?listing_id=${this.state.listing.id}`).then(response => {
                if (response.ok)
                    return response.json();
                throw new Error('Could not load inventory data.')
            }).then(results => {
                this.setState({
                    inventories: results
                })
            })

        }).catch(e => {
            this.setState({
                loading: false,
                vendor: {}
            })
        })
    }

    componentDidUpdate (prevProps, prevState) {
        if (this.props.match.listingId !== prevProps.match.listingId)
            this.componentDidMount()
    }

    render () {
        return (
            <div>
                {this.state.loading
                    ? <span>Loading...</span>
                    : <div>
                        <VendorDetails
                            loading={this.state.loading}
                            vendor={this.state.vendor}
                        />
                        <ListingDetails
                            loading={this.state.loading}
                            listing={this.state.listing}
                        />
                        <ExtraDetails
                            loading={this.state.loading}
                            data={this.state.listing.extra}
                        />
                        <InventoryList
                            loading={this.state.loading}
                            total={this.state.inventories.total}
                            inventories={this.state.inventories.items}
                        />
                        <pre>{JSON.stringify(this.state, null, '  ')}</pre>
                    </div>}
            </div>
        )
    }
}