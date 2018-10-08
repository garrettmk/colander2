import React from "react";

import ExtensionContext, { ExtensionProvider } from "./Context/ExtensionContext";
import ExtensionActions from "./ExtensionActions";

import { DocumentContext } from "./Context/DocumentContext";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function VendorActions (props) {
    return (
        <DocumentContext.Consumer>
            { ({ doc }) => (
                <ExtensionContext.Consumer>
                    { ext => {
                        const exports = ext.extension.exports ? Object.keys(ext.extension.exports) : [];
                        let actions = [];

                        if (exports.indexOf('UpdateListings') >= 0)
                            actions.push({
                                name: "Update all listings",
                                action: 'UpdateListings',
                                context: {
                                    query: { vendor_id: doc.id }
                                }
                            });

                        if (exports.indexOf('ImportInventory') >=0)
                            actions.push({
                                name: 'Import inventory',
                                action: 'ImportMatchingListings',
                                context: {
                                    vendor_id: doc.id
                                }
                            });

                        if (exports.indexOf('ImportInboundOrders') >= 0)
                            actions.push({
                                name: 'Import inbound orders',
                                action: 'ImportInboundOrders',
                                context: {
                                    vendor_id: doc.id
                                }
                            });

                        if (exports.indexOf('ImportOrders') >= 0)
                            actions.push({
                                name: 'Import customer orders',
                                action: 'ImportOrders',
                                context: {
                                    vendor_id: doc.id
                                }
                            });

                        if (exports.indexOf('ImportFinancials') >= 0)
                            actions.push({
                                name: 'Import financial data',
                                action: 'ImportFinancials',
                                context: {
                                    vendor_id: doc.id
                                }
                            });

                        return <ExtensionActions presets={actions} editor/>;
                    }}
                </ExtensionContext.Consumer>
            )}
        </DocumentContext.Consumer>
    )
}


export function CoreVendorActions (props) {
    return (
        <DocumentContext.Consumer>
            { ({ doc }) => {
                const presets = [
                    {
                        name: 'Import matching listings',
                        action: 'ImportMatchingListings',
                        context: {
                            query: { vendor_id: doc.id }
                        }
                    }
                ]

                return (
                    <ExtensionProvider extId={1}>
                        <ExtensionActions presets={presets}/>
                    </ExtensionProvider>
                )
            }}
        </DocumentContext.Consumer>
    )
}