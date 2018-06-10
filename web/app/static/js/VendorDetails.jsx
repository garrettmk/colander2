import React from "react";
import { fetchVendor } from "./colander";


export default class VendorDetails extends React.Component {

    constructor (props) {
        super(props);

        this.state = {
            loading: true,
            vendor: {}
        }
    }

    componentDidMount () {
        this.setState({
            loading: true
        });

        fetchVendor(this.props.vendorId, { getAttrs: ['abbreviated'] }).then(response => {
            if (response.ok)
                return response.json();
        }).then(results => {
            this.setState({
                loading: false,
                vendor: results.items[0]
            })
        }).catch(error => {
            alert(error);
            this.setState({
                loading: false,
                vendor: {}
            })
        })
    }

    render () {
        return (
            <div className={"outlined"}>
            {this.state.loading
                ? 'Loading...'
                : <div>
                    <h4>{this.state.vendor.name}</h4>
                    <h5><a href={this.state.vendor.url} target="_blank">{this.state.vendor.url}</a></h5>
                    <ul>
                        <li>Avg. Shipping: {this.state.vendor.avg_shipping}</li>
                        <li>Avg: Tax: {this.state.vendor.avg_tax}</li>
                        <li>Extension: {this.state.vendor.ext_module || 'None'}</li>
                    </ul>
                </div>}
            </div>
        )
    }
}
