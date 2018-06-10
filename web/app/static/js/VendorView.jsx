import React from "react";
import update from "immutability-helper";
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

        fetch(`/api/obj/vendor?vendor_id=${vendorId}&getAttrs=foreign_inventories`).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Could not fetch inventory data.')
        }).then(results => {
            this.setState({
                inventories: {
                    loading: false,
                    total: results.items[0].foreign_inventories.total,
                    items: results.items[0].foreign_inventories.inventories
                }
            })
        }).catch(error => {
            this.setState({
                inventories: { loading: false, total: null, items: [] }
            })
        })
    }

    // componentDidMount () {
    //     const vendorId = this.props.match.params.vendorId;
    //     this.fetchVendor(vendorId);
    //     // this.fetchListings(vendorId);
    //     // this.fetchInventories(vendorId);
    // }
    //
    // componentDidUpdate (prevProps, prevState) {
    //     const newVendorId = this.props.match.params.vendorId;
    //     const oldVendorId = prevProps.match.params.vendorId;
    //     if (newVendorId !== oldVendorId) {
    //         this.fetchVendor(newVendorId);
    //         // this.fetchListings(newVendorId);
    //         // this.fetchInventories(newVendorId);
    //     }
    // }

    render () {
        const vendorId = this.props.match.params.vendorId;

        return (
            <div>
                <h2>Vendor View</h2>
                <div>
                    <VendorDetails vendorId={vendorId}/>
                    <ExtraDetails objType={"vendor"} objId={vendorId}/>
                    <ExtensionAction vendorId={vendorId}/>
                    <InventoryList ownerId={vendorId} own={true}/>
                    {/*<ListingsList vendorId={vendorId}/>*/}
                </div>
            </div>
        )
    }
}