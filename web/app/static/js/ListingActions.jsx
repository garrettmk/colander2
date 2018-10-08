import React from "react";

import ExtensionContext, { ExtensionProvider } from "./Context/ExtensionContext";
import ExtensionActions from "./ExtensionActions";

import { DocumentContext } from "./Context/DocumentContext";


////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


export function ListingActions (props) {
    return (
        <DocumentContext.Consumer>
            { ({ doc }) => (
                <ExtensionContext.Consumer>
                    { ext => {
                        const exports = ext.extension.exports ? Object.keys(ext.extension.exports) : [];
                        let actions = [];

                        if (exports.indexOf('UpdateListings') >= 0)
                            actions.push({
                                name: "Update listing",
                                action: 'UpdateListings',
                                context: {
                                    query: { id: doc.id }
                                }
                            });

                        if (exports.indexOf('ImportMatchingListings') >= 0)
                            actions.push({
                                name: 'Find similar',
                                action: 'ImportMatchingListings',
                                context: {
                                    listing_id: doc.id
                                }
                            });

                        return <ExtensionActions presets={actions}/>;
                    }}
                </ExtensionContext.Consumer>
            )}
        </DocumentContext.Consumer>
    )
}


export function CoreListingActions (props) {
    return (
        <DocumentContext.Consumer>
            { ({ doc }) => {
                const actions = [
                    {
                        name: 'Find matching listings',
                        action: 'ImportMatchingListings',
                        context: {listing_id: doc.id}
                    },
                ];

                return (
                    <ExtensionProvider extId={1}>
                        <ExtensionActions presets={actions}/>
                    </ExtensionProvider>
                )
            }}
        </DocumentContext.Consumer>
    )
}