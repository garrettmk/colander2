import React from "react";
import VendorDetails from "./VendorDetails";
import ListingsList from "./ListingsList";
import ArgumentsEditor from "./ArgumentsEditor";


export default class VendorView extends React.Component {

    constructor (props) {
        super(props);

        this.state = {
            loading: true,
            vendor: {
                listings: {
                    total: 0,
                    listings: []
                },
                extension: []
            }
        };

        this.fetchVendor = this.fetchVendor.bind(this);
    }

    fetchVendor () {
        const vendor_id = this.props.match.params.vendorId;
        this.setState({
            loading: true
        });

        fetch(`/api/obj/vendor?id=${vendor_id}&getAttrs=all`).then(response => {
            if (response.ok)
                return response.json();
            throw new Error('Getting vendor details failed.')
        }).then(results => {
            console.log(results.items[0]);
            this.setState({
                loading: false,
                vendor: results.items[0]
            })
        }).catch(error => {
            this.setState({
                loading: false,
                vendor: {}
            });
            alert(error);
        })
    }
    componentDidMount () {
        this.fetchVendor(this.props.match.params.vendorId)
    }

    componentDidUpdate (prevProps, prevState) {
        if (this.props.match.vendorId !== prevProps.match.vendorId)
            this.fetchVendor()
    }

    render () {
        return (
            <div>
                <h2>Vendor View</h2>
                <ArgumentsEditor/>
                <VendorDetails
                    loading={this.state.loading}
                    vendor={this.state.vendor}
                />
                <ListingsList
                    loading={this.state.loading}
                    total={this.state.vendor.listings.total}
                    listings={this.state.vendor.listings.listings}
                />
            </div>
        )
    }
}