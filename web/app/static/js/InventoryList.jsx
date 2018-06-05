import React from "react";
import { Link } from "react-router-dom";


export default function InventoryList (props) {

    return (
        <div className={"outlined"}>
            <h3>{props.title} {props.loading ? '' : '(' + props.total + ')'}</h3>
            {props.loading
                ? 'Loading...'
                : <table>
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Owner</th>
                            <th>Listing</th>
                            <th>Active</th>
                            <th>Fulfillable</th>
                        </tr>
                    </thead>
                    <tbody>
                    {props.inventories.map(inv => {
                        return (
                            <tr key={inv.id}>
                                <td>{inv.id}</td>
                                <td>{inv.owner.name}</td>
                                <td>{inv.listing.sku}</td>
                                <td>{inv.active}</td>
                                <td>{inv.fulfillable}</td>
                            </tr>
                        )
                    })}
                    </tbody>
                </table>
            }
        </div>
    )
}