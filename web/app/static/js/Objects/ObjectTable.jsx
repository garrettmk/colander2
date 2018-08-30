import React from "react";
import PropTypes from "prop-types";
import { Link } from "react-router-dom";
import update from "immutability-helper";

import { Segment, Table, Checkbox, Image, Icon, Pagination } from "semantic-ui-react";

import { DocumentContext, QueryContext, CollectionContext, SelectionContext, IndexProvider } from "../Contexts";
import { asCount, asCurrency, asPercent } from "../style";
import { defaultImages } from "../style";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function HeaderCell (props) {
    const { field: path } = props;

    return (
        <CollectionContext.Consumer>
            { ({ schemas, type }) => {
                const steps = path.split('.');
                const field = steps[steps.length - 1];

                // Get the field schema
                let ref, schema = schemas[type];
                for (let step of steps) {
                    ref = schema && schema.properties && schema.properties[step] && schema.properties[step].$ref
                        ? schema.properties[step].$ref.split('/').reverse()[0]
                        : undefined;

                    schema = ref ? schemas[ref] : schema.properties[step];
                }

                let options = {}, label, suffix;
                if (schema) {
                    label = schema
                        ? schema.label || schema.title || schema.name || field
                        : field;

                    switch (schema.type) {
                        case 'number':
                            options.textAlign = 'right';
                            break;
                    }

                    switch (schema.format) {
                        case 'percent':
                            suffix = '(%)';
                            break;
                    }
                } else {
                    label = field;
                }

                return (
                    <QueryContext.Consumer>
                        { ({ query, updateQuery }) => {
                            const direction = query && query._sort && query._sort[path];
                            const otherDirection = direction === 'ascending' ? 'descending' : 'ascending';
                            const handleSort = () => updateQuery(update(query, {$merge: { _sort: { [path]: otherDirection}}}));

                            return (
                                <Table.HeaderCell sorted={direction} onClick={schema ? handleSort : undefined} {...options}>
                                    {suffix ? `${label} (${suffix})` : label}
                                </Table.HeaderCell>
                            )

                        }}
                    </QueryContext.Consumer>
                )
            }}
        </CollectionContext.Consumer>
    )
}


HeaderCell.propTypes = {
    field: PropTypes.string.isRequired
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function valueFromPath(doc, path) {
    let steps = path.split('.');
    if (steps.length === 1)
        return doc[path];
    else if (steps.length > 1)
        return valueFromPath(doc[steps[0]], steps.slice(1).join('.'));
    else
        return undefined;
}


const customFields = {
    Listing: {
        Vendor: obj => obj && obj.vendor ? obj.vendor.name : 'n/a',
        'Vendor/SKU': obj => (
            <span>
                <b>{obj.vendor.name}</b><br/>
                {obj.sku}
            </span>
        ),
        Image: obj => <Image src={obj.image_url || defaultImages[obj.type].light} size={'tiny'}/>,
        Summary: obj => (
            <div>
                <Link to={`/Listing/${obj.id}`}>{obj.title}</Link>
                <div style={{ display: 'flex', flexDirection: 'row' }}>
                    <span style={{ marginRight: '3em'}}><b>Category: </b>{obj.category || 'n/a'}</span>
                    <span><b>Rank: </b>{obj.rank || 'n/a'}</span>
                </div>
            </div>
        ),
        Score: obj => asPercent(obj._score)
    }
};


function Cell (props) {
    const { field: path, customFields } = props;

    return (
        <DocumentContext.Consumer>
            { ({ schemas, type, doc }) => {

                const steps = path.split('.');
                const field = steps[steps.length - 1];
                let value, options = {};

                if (customFields[type] && customFields[type][field]) {
                    value = customFields[type][field](doc)
                } else {
                    // Get the field schema
                    let ref, schema = schemas[type];
                    for (let step of steps) {
                        ref = schema.properties[step].$ref
                            ? schema.properties[step].$ref.split('/').reverse()[0]
                            : undefined;

                        schema = ref ? schemas[ref] : schema.properties[step];
                    }

                    // Get the value
                    value = doc ? valueFromPath(doc, path) : undefined;

                    // Formatting
                    switch (schema.type) {
                        case 'number':
                            options.textAlign = 'right';
                            break;
                    }

                    switch (schema.format) {
                        case 'decimal':
                            value = asCurrency(value);
                            break;

                        case 'percent':
                            value = asPercent(value);
                            break;

                        case 'integer':
                            value = asCount(value);
                            break;
                    }
                }

                return (
                    <Table.Cell {...options}>
                        {value}
                    </Table.Cell>
                )
            }}
        </DocumentContext.Consumer>
    )
}


Cell.propTypes = {
    field: PropTypes.string.isRequired,
    customFields: PropTypes.object,
};


Cell.defaultProps = {
    customFields: customFields
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


function SelectCell (props) {
    const { header } = props;

    return (
        <SelectionContext.Consumer>
            { ({ ids, toggleSelected }) => (
                <DocumentContext.Consumer>
                    { ({ doc }) => (
                        React.createElement(
                            header? Table.HeaderCell : Table.Cell,
                            null,
                            <Checkbox
                                disabled={!doc}
                                checked={doc && ids.has(doc.id)}
                                onChange={() => toggleSelected([doc.id])}
                            />
                        )
                    )}
                </DocumentContext.Consumer>
            )}
        </SelectionContext.Consumer>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function ObjectTable (props) {
    let { as, asProps, only, exclude, tableProps, select } = props;

    if (!as) {
        as = Segment;
        if (asProps.raised === undefined)
            asProps.raised = true;
    }

    return (
        <CollectionContext.Consumer>
            { coll => {
                const schema = coll.schemas[coll.type];
                const { properties = {}, required = [], } = schema || {};
                const fields = (only || Object.keys(properties)).filter(key => !exclude.includes(key));
                const columnCount = fields.length + (select ? 1 : 0);

                return React.createElement(as, asProps,
                    coll.loading || !schema
                        ? <React.Fragment/>
                        : <Table sortable selectable {...tableProps}>
                            <Table.Header>
                                <Table.Row>
                                    {select && <Table.HeaderCell/>}
                                    {fields.map(field => (
                                        <HeaderCell key={field} field={field}/>
                                    ))}
                                </Table.Row>
                            </Table.Header>
                            <Table.Body>
                                {coll.items.length
                                    ? coll.items.map((obj, idx) => (
                                        <Table.Row key={obj.id}>
                                            <IndexProvider index={idx}>
                                                {select && <SelectCell/>}
                                                {fields.map(field => <Cell key={field} field={field}/>)}
                                            </IndexProvider>
                                        </Table.Row>
                                    ))
                                    : <Table.Row>
                                        {select && <Table.Cell/>}
                                        <Table.Cell colSpan={columnCount}>
                                            No items to display.
                                        </Table.Cell>
                                    </Table.Row>
                                }
                            </Table.Body>
                            <Table.Footer>
                                <Table.Row>
                                    <Table.HeaderCell textAlign={'right'} colSpan={columnCount}>
                                        <QueryContext.Consumer>
                                            { ({ view, setView }) => (
                                                <Pagination
                                                    totalPages={coll.pages}
                                                    activePage={coll.page}
                                                    onPageChange={(e, { activePage }) =>
                                                        setView(
                                                            update(
                                                                view,
                                                                {$merge: {
                                                                    _page: activePage
                                                                }}))
                                                    }
                                                />
                                            )}
                                        </QueryContext.Consumer>
                                    </Table.HeaderCell>
                                </Table.Row>
                            </Table.Footer>
                        </Table>
                )
            }}
        </CollectionContext.Consumer>
    )
}


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


ObjectTable.propTypes = {
    as: PropTypes.oneOfType([PropTypes.string, PropTypes.func]),
    asProps: PropTypes.object,
    only: PropTypes.arrayOf(PropTypes.string),
    exclude: PropTypes.arrayOf(PropTypes.string),
    tableProps: PropTypes.object,
    select: PropTypes.bool
};


ObjectTable.defaultProps = {
    as: Segment,
    asProps: { raised: true },
    only: undefined,
    exclude: [],
    tableProps: {},
    select: false
};


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////