import React from "react";


export default function VendorDetails (props) {
    return (
        <div>
        {props.loading
            ? <h4>Loading...</h4>
            : <div>
                <h4>{props.vendor.name}</h4>
                    <h5><a href={props.vendor.url} target="_blank">{props.vendor.url}</a></h5>
                    <h5>Highlights</h5>
                    <ul>
                        <li>Total listings: {props.vendor.listings.total}</li>
                        <li>Avg. Shipping: {props.vendor.avg_shipping}</li>
                        <li>Avg: Tax: {props.vendor.avg_tax}</li>
                    </ul>
                    <h5>Extension: {props.vendor.ext_module || 'None'}</h5>
                    <ul>
                        {props.vendor.extension.map(exp => <li key={exp}>{exp}</li>)}
                    </ul>
            </div>}
        </div>
    )
}