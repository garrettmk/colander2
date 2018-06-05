import React from "react";


export default function VendorDetails (props) {
    return (
        <div className={"outlined"}>
        {props.loading
            ? <h4>Loading...</h4>
            : <div>
                <h4>{props.vendor.name}</h4>
                <h5><a href={props.vendor.url} target="_blank">{props.vendor.url}</a></h5>
                <ul>
                    {props.vendor.listings
                        ? <li>Total listings: {props.vendor.listings.total}</li>
                        : <span>n/a</span>
                    }
                    <li>Avg. Shipping: {props.vendor.avg_shipping}</li>
                    <li>Avg: Tax: {props.vendor.avg_tax}</li>
                    <li>Extension: {props.vendor.ext_module || 'None'}</li>
                </ul>
            </div>}
        </div>
    )
}