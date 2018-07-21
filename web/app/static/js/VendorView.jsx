import React from "react";
import { Grid, Segment, Table, Image, Header } from "semantic-ui-react";
import _ from "lodash";

import { asCurrency, asCount } from "./App";
import Colander from "./colander";
import EntityDetails from "./ObjectDetails";
import ExtraDetails from "./ExtraDetails";
import ObjectTable from "./ObjectTable";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function VendorDetails (props) {
    const { id } = props;

    return (
        <EntityDetails
            type={'vendor'}
            id={id}
            strict
            extra
            format={{
                avg_shipping: vnd => ({label: 'Avg. Shipping', value: <span>{vnd.avg_shipping * 100 + '%'}</span>}),
                avg_tax: vnd => ({label: 'Avg. Tax', value: <span>{vnd.avg_tax * 100 + '%'}</span>}),
            }}
        />
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function ListingTable (props) {
    const { query } = props;

    const columns = [
        {label: 'ID', value: 'id', sort: 'id' },
        {label: 'Vendor/SKU', value: obj => <a href={obj.detail_url} target="_blank">{obj.vendor.name}<br/>{obj.sku}</a>, sort: 'vendor_id'},
        {label: 'Image', value: obj => <Image size={'tiny'} src={obj.image_url}/>},
        {label: 'Title', value: 'title'},
        {label: 'Price', value: obj => asCurrency(obj.price), format: { textAlign: 'right'}, sort: 'price' }
    ];

    const view = { vendor: { _only: ['name'] } };

    return <ObjectTable
        type={'listing'}
        columns={columns}
        query={query}
        view={view}
    />
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export default class VendorView extends React.Component {

    constructor (props) {
        super(props);
    }

    render () {
        const vendorId = this.props.match.params.vendorId;
        const listingQuery = { vendor_id: vendorId };

        return (
            <Grid columns={2}>
                <Grid.Column width={4}>
                    <VendorDetails id={vendorId}/>
                </Grid.Column>
                <Grid.Column width={12}>
                    <ListingTable query={listingQuery}/>
                    <ExtraDetails type={"vendor"} id={vendorId}/>
                </Grid.Column>
            </Grid>
        )
    }
}