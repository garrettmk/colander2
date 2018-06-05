import React from "react";
import VendorDetails from "./VendorDetails";
import ListingsList from "./ListingsList";
import ExtensionAction from "./ExtensionAction";
import { fetchVendor } from "./colander";
import ExtraDetails from "./ExtraDetails";
import InventoryList from "./InventoryList";


export default class VendorView extends React.Component {

    constructor (props) {
        super(props);

        this.defaultState = this.defaultState.bind(this);
        this.fetchVendor = this.fetchVendor.bind(this);
        this.sendExtAction = this.sendExtAction.bind(this);

        this.state = this.defaultState();
    }

    defaultState () {
        return {
            vendor: {
                loading: true,
                vendor: {}
            },
            listings: {
                loading: true,
                total: null,
                items: []
            },
            extension: {
                loading: true,
                actions: []
            },
            inventories: {
                loading: true,
                items: []
            }
        };
    }

    fetchVendor (vendorId) {
        this.setState({
            vendor: { loading: true, vendor: {} }
        });

        fetchVendor(vendorId).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Getting vendor details failed.')
        }).then(results => {
            this.setState({
                vendor: {
                    loading: false,
                    vendor: results.items[0]
                }
            })
        }).catch(error => {
            this.setState({
                loading: false,
                vendor: {}
            });
            alert(error);
        })
    }

    fetchListings (vendorId) {
        this.setState({
            listings: { loading: true, total: null, items: [] }
        });

        fetch(`/api/obj/listing?vendor_id=${vendorId}&getAttrs=abbreviated`).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch listings.')
        }).then(results => {
            this.setState({
                listings: {
                    loading: false,
                    total: results.total,
                    items: results.items
                }
            })
        }).catch(error => {
            this.setState({
                listings: { loading: false, total: null, items: [] }
            })
        })
    }

    fetchInventories (vendorId) {
        this.setState({
            inventories: { loading: true, total: null, items: [] }
        });

        fetch(`/api/obj/inventory?owner_id=${vendorId}&getAttrs=all`).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch inventory data.')
        }).then(results => {
            this.setState({
                inventories: {
                    loading: false,
                    total: results.total,
                    items: results.items
                }
            })
        }).catch(error => {
            this.setState({
                inventories: { loading: false, total: null, items: [] }
            })
        })
    }

    sendExtAction (data) {
        fetch('/api/tasks', {
            body: JSON.stringify(data),
            headers: {
              'content-type': 'application/json'
            },
            method: 'POST'
        }).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Failed')
        }).then(results => {
            console.log(results)
        })
    }

    componentDidMount () {
        const vendorId = this.props.match.params.vendorId;
        this.fetchVendor(vendorId);
        this.fetchListings(vendorId);
        this.fetchInventories(vendorId);
    }

    componentDidUpdate (prevProps, prevState) {
        const newVendorId = this.props.match.params.vendorId;
        const oldVendorId = prevProps.match.params.vendorId;
        if (newVendorId !== oldVendorId) {
            this.fetchVendor(newVendorId);
            this.fetchListings(newVendorId);
            this.fetchInventories(newVendorId);
        }
    }

    render () {
        return (
            <div>
                <h2>Vendor View</h2>
                <div>
                    <VendorDetails
                        loading={this.state.vendor.loading}
                        vendor={this.state.vendor.vendor}
                    />
                    <ExtraDetails
                        loading={this.state.vendor.loading}
                        data={this.state.vendor.vendor.extra}
                    />
                    <ExtensionAction
                        name={this.state.vendor.ext_module}
                        module={this.state.vendor.ext_module}
                        actions={this.state.vendor.extension || []}
                        onSubmit={this.sendExtAction}
                    />
                    <InventoryList
                        title={"Inventories"}
                        loading={this.state.inventories.loading}
                        total={this.state.inventories.total}
                        inventories={this.state.inventories.items}
                    />
                    <ListingsList
                        loading={this.state.listings.loading}
                        total={this.state.listings.total}
                        listings={this.state.listings.items}
                    />
                </div>
            </div>
        )
    }
}