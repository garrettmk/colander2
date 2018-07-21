import React from "react";
import _ from "lodash";
import { Grid } from "semantic-ui-react";

import { asCount, asCurrency, asPercent } from "./App";
import ObjectDetails from "./ObjectDetails";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function ListingDetails (props) {
    const { id } = props;

    return <ObjectDetails
        type={'listing'}
        id={id}
        view={{ vendor: { _only: ['name'] } }}
        strict
        extra
        format={{
            last_modified: lst => ({ label: 'Last Modified', value: lst.last_modified}),
            vendor: lst => ({ label: 'Vendor', value: lst.vendor ? lst.vendor.name : 'n/a' }),
            sku: lst => ({ label: 'SKU', value: lst.sku }),
            brand: lst => ({ label: 'Brand', value: lst.brand }),
            model: lst => ({ label: 'Model', value: lst.model }),
            price: lst => ({ label: 'Price', value: asCurrency(lst.price) }),
            quantity: lst => ({ label: 'Quantity', value: asCount(lst.quantity) }),
            category: lst => ({ label: 'Category', value: lst.extra ? lst.extra.category : 'n/a' }),
            rank: lst => ({ label: 'Rank', value: asCount(lst.rank) }),
            rating: lst => ({ label: 'Rating', value: asPercent(lst.rating) })
        }}
    />
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default class ListingView extends React.Component {

    constructor(props) {
        super(props);

        this.state = {
            loading: true,
            listing: {},
        };
    }

    render () {
        const listingId = this.props.match.params.listingId;

        return (
            <Grid columns={2}>
                <Grid.Column width={4}>
                    <ListingDetails id={listingId}/>
                </Grid.Column>
                <Grid.Column width={12}>
                </Grid.Column>
            </Grid>
        )
    }

}