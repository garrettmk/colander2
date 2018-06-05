import React from "react";


export default function ListingDetails (props) {
    return (
        <div className="outlined">
            {props.loading
                ? <h4>Loading...</h4>
                : <div>
                    <h4>{props.listing.title}</h4>
                    <h5><a href={props.listing.detail_url} target="_blank">{props.listing.detail_url}</a></h5>
                    <ul>
                        <li>SKU: {props.listing.sku}</li>
                        <li>Brand: {props.listing.brand}</li>
                        <li>Model: {props.listing.model}</li>
                        <li>Quantity: {props.listing.quantity}</li>
                        <li>Price: ${props.listing.price}</li>
                    </ul>
                </div>}
        </div>
    )
}